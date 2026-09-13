from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

from sqlalchemy import func, select

from app.db.models import InventoryTransactionModel, ProductModel, ProductVariantModel
from app.domain.errors import ConflictError
from app.services.inventory import adjust_inventory
from tests.conftest import TestContext, onboard_product


def test_variants_and_inventory_adjustments_are_idempotent(
    authenticated: tuple[TestContext, dict[str, str]],
) -> None:
    context, headers = authenticated
    product_id = f"VAR{uuid.uuid4().hex[:8]}"
    onboard_product(context, headers, product_id, stock="5")

    initial = context.client.get(f"/api/v1/products/{product_id}/variants", headers=headers)
    assert initial.status_code == 200, initial.text
    assert [(item["variant_id"], item["stock"]) for item in initial.json()] == [("default", 5)]

    added = context.client.post(
        f"/api/v1/products/{product_id}/variants",
        headers=headers,
        json={
            "variant_id": "red-large",
            "title": "Red / Large",
            "sku": f"{product_id}-RL",
            "options": {"color": "red", "size": "large"},
            "price": "1099.00",
            "stock": 3,
            "stock_policy": "deny",
        },
    )
    assert added.status_code == 201, added.text
    assert added.json()["options"] == {"color": "red", "size": "large"}
    history = context.client.get(
        f"/api/v1/products/{product_id}/inventory/transactions", headers=headers
    ).json()
    creation = [entry for entry in history if entry["variant_id"] == "red-large"]
    assert len(creation) == 1
    assert creation[0]["quantity_before"] == 0
    assert creation[0]["quantity_after"] == creation[0]["delta"] == 3
    assert creation[0]["actor_user_id"] is not None

    ambiguous = context.client.post(
        f"/api/v1/products/{product_id}/inventory/adjust",
        headers=headers,
        json={
            "delta": -1,
            "reason": "manual",
            "idempotency_key": f"ambiguous-{uuid.uuid4().hex}",
        },
    )
    assert ambiguous.status_code == 409

    key = f"inventory-{uuid.uuid4().hex}"
    payload = {
        "variant_id": "red-large",
        "delta": -2,
        "reason": "manual_correction",
        "idempotency_key": key,
        "reference_type": "stocktake",
        "reference_id": "count-2026-07",
    }
    first = context.client.post(
        f"/api/v1/products/{product_id}/inventory/adjust",
        headers=headers,
        json=payload,
    )
    second = context.client.post(
        f"/api/v1/products/{product_id}/inventory/adjust",
        headers=headers,
        json=payload,
    )
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["quantity_after"] == second.json()["quantity_after"]
    assert first.json()["quantity_after"] == 1

    too_low = context.client.post(
        f"/api/v1/products/{product_id}/inventory/adjust",
        headers=headers,
        json={
            "variant_id": "red-large",
            "delta": -2,
            "reason": "manual_correction",
            "idempotency_key": f"inventory-{uuid.uuid4().hex}",
        },
    )
    assert too_low.status_code == 409

    with context.session_factory() as session:
        product = session.scalar(select(ProductModel).where(ProductModel.product_id == product_id))
        variant = session.scalar(
            select(ProductVariantModel).where(
                ProductVariantModel.product_pk == product.id,
                ProductVariantModel.variant_id == "red-large",
            )
        )
        transaction_count = session.scalar(
            select(func.count(InventoryTransactionModel.id)).where(
                InventoryTransactionModel.store_id == "demo-store",
                InventoryTransactionModel.idempotency_key == key,
            )
        )
        assert product is not None and product.stock == 6
        assert variant is not None and variant.stock == 1
        assert transaction_count == 1


def test_order_creation_is_idempotent_and_reserves_selected_variant_once(
    authenticated: tuple[TestContext, dict[str, str]],
) -> None:
    from tests.api.test_orders import _conversation_id

    context, headers = authenticated
    product_id = f"ORDVAR{uuid.uuid4().hex[:8]}"
    onboard_product(context, headers, product_id, stock="4")
    reviewed = context.client.patch(
        f"/api/v1/products/{product_id}",
        headers=headers,
        json={"description": "Reviewed sellable variant product.", "price": "1234.56"},
    )
    assert reviewed.status_code == 200, reviewed.text
    activated = context.client.post(f"/api/v1/products/{product_id}/activate", headers=headers)
    assert activated.status_code == 200, activated.text
    request_key = f"order-create-{uuid.uuid4().hex}"
    payload = {
        "conversation_id": _conversation_id(context),
        "items": [{"product_id": product_id, "variant_id": "default", "quantity": 2}],
        "discount": "10.00",
        "shipping_total": "25.00",
        "tax_total": "5.00",
        "currency": "EGP",
        "shipping": {"city": "Cairo"},
        "idempotency_key": request_key,
    }
    first = context.client.post("/api/v1/orders", headers=headers, json=payload)
    second = context.client.post("/api/v1/orders", headers=headers, json=payload)
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["shipping_total"] == "25.00"
    assert first.json()["tax_total"] == "5.00"
    assert first.json()["items"][0]["variant_id"] == "default"
    assert first.json()["items"][0]["unit_price"] == "1234.56"

    order_id = first.json()["id"]
    pending = context.client.post(
        f"/api/v1/orders/{order_id}/transition",
        headers=headers,
        json={"status": "pending", "reason": "reserve"},
    )
    retry = context.client.post(
        f"/api/v1/orders/{order_id}/transition",
        headers=headers,
        json={"status": "pending", "reason": "retry"},
    )
    assert pending.status_code == 200, pending.text
    assert retry.status_code == 409

    with context.session_factory() as session:
        variant = session.scalar(
            select(ProductVariantModel).where(
                ProductVariantModel.store_id == "demo-store",
                ProductVariantModel.variant_id == "default",
                ProductVariantModel.product_pk
                == select(ProductModel.id)
                .where(
                    ProductModel.store_id == "demo-store",
                    ProductModel.product_id == product_id,
                )
                .scalar_subquery(),
            )
        )
        reservation_count = session.scalar(
            select(func.count(InventoryTransactionModel.id)).where(
                InventoryTransactionModel.store_id == "demo-store",
                InventoryTransactionModel.reference_type == "order",
                InventoryTransactionModel.reference_id == str(order_id),
                InventoryTransactionModel.reason == "order_reservation",
            )
        )
        assert variant is not None and variant.stock == 2
        assert reservation_count == 1
    cancelled = context.client.post(
        f"/api/v1/orders/{order_id}/transition",
        headers=headers,
        json={"status": "cancelled", "reason": "test_cleanup"},
    )
    assert cancelled.status_code == 200, cancelled.text


def test_concurrent_inventory_adjustments_cannot_oversell(
    authenticated: tuple[TestContext, dict[str, str]],
) -> None:
    context, headers = authenticated
    product_id = f"RACE{uuid.uuid4().hex[:8]}"
    onboard_product(context, headers, product_id, stock="1")

    def reserve(index: int) -> str:
        try:
            with context.session_factory.begin() as session:
                adjust_inventory(
                    session,
                    store_id="demo-store",
                    product_id=product_id,
                    variant_id="default",
                    delta=-1,
                    reason="concurrency_test",
                    idempotency_key=f"race:{product_id}:{index}",
                )
            return "accepted"
        except ConflictError:
            return "blocked"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(reserve, range(2)))

    assert sorted(outcomes) == ["accepted", "blocked"]
    with context.session_factory() as session:
        product = session.scalar(
            select(ProductModel).where(
                ProductModel.store_id == "demo-store",
                ProductModel.product_id == product_id,
            )
        )
        variant = session.scalar(
            select(ProductVariantModel).where(
                ProductVariantModel.store_id == "demo-store",
                ProductVariantModel.product_pk == product.id,
                ProductVariantModel.variant_id == "default",
            )
        )
        accepted = session.scalar(
            select(func.count(InventoryTransactionModel.id)).where(
                InventoryTransactionModel.store_id == "demo-store",
                InventoryTransactionModel.product_pk == product.id,
                InventoryTransactionModel.reason == "concurrency_test",
            )
        )
        assert product is not None and product.stock == 0
        assert variant is not None and variant.stock == 0
        assert accepted == 1
    with context.session_factory.begin() as session:
        adjust_inventory(
            session,
            store_id="demo-store",
            product_id=product_id,
            variant_id="default",
            delta=10,
            reason="test_cleanup",
            idempotency_key=f"cleanup:{product_id}",
        )


def test_external_catalog_blocks_manual_variant_and_stock_mutations(
    authenticated: tuple[TestContext, dict[str, str]],
) -> None:
    context, headers = authenticated
    product_id = f"EXT{uuid.uuid4().hex[:8]}"
    onboard_product(context, headers, product_id, stock="5")
    with context.session_factory.begin() as session:
        row = session.scalar(select(ProductModel).where(ProductModel.product_id == product_id))
        assert row is not None
        row.source_of_truth = "external"
        row.source_provider = "shopify"
    path = f"/api/v1/products/{product_id}"
    adjustment = context.client.post(
        f"{path}/inventory/adjust",
        headers=headers,
        json={"delta": 2, "reason": "manual", "idempotency_key": uuid.uuid4().hex},
    )
    assert adjustment.status_code == 409, adjustment.text
    creation = context.client.post(
        f"{path}/variants",
        headers=headers,
        json={
            "variant_id": "extra",
            "title": "Extra",
            "sku": f"{product_id}-extra",
            "price": "10.00",
            "stock": 2,
        },
    )
    assert creation.status_code == 409, creation.text
    assert context.client.get(path, headers=headers).json()["stock"] == 5
    assert len(context.client.get(f"{path}/variants", headers=headers).json()) == 1


@pytest.mark.parametrize(
    "field,value",
    [("delta", 3), ("reason", "different"), ("reference_id", "other"), ("variant_id", "different")],
)
def test_inventory_key_cannot_hide_a_different_request(
    authenticated: tuple[TestContext, dict[str, str]],
    field: str,
    value: object,
) -> None:
    context, headers = authenticated
    product_id = f"KEY{uuid.uuid4().hex[:8]}"
    onboard_product(context, headers, product_id, stock="5")
    path = f"/api/v1/products/{product_id}/inventory/adjust"
    payload = {
        "variant_id": "default",
        "delta": 1,
        "reason": "stocktake",
        "reference_id": "count1",
        "idempotency_key": uuid.uuid4().hex,
    }
    first = context.client.post(path, headers=headers, json=payload)
    assert first.status_code == 200, first.text
    replay = context.client.post(path, headers=headers, json=payload)
    assert replay.status_code == 200 and replay.json()["id"] == first.json()["id"]
    changed = context.client.post(path, headers=headers, json={**payload, field: value})
    assert changed.status_code == 409, changed.text
    wrong_product = context.client.post(
        "/api/v1/products/MISSING/inventory/adjust", headers=headers, json=payload
    )
    assert wrong_product.status_code in {404, 409}, wrong_product.text
    assert (
        context.client.get(f"/api/v1/products/{product_id}", headers=headers).json()["stock"] == 6
    )


def test_permitted_negative_inventory_can_be_read_back(
    authenticated: tuple[TestContext, dict[str, str]],
) -> None:
    context, headers = authenticated
    product_id = f"NEG{uuid.uuid4().hex[:8]}"
    onboard_product(context, headers, product_id, stock="10")
    path = f"/api/v1/products/{product_id}"
    result = context.client.post(
        f"{path}/inventory/adjust",
        headers=headers,
        json={
            "delta": -11,
            "reason": "stocktake",
            "allow_negative": True,
            "idempotency_key": uuid.uuid4().hex,
        },
    )
    assert result.status_code == 200 and result.json()["quantity_after"] == -1
    variants = context.client.get(f"{path}/variants", headers=headers)
    assert variants.status_code == 200, variants.text
    assert variants.json()[0]["stock"] == -1
    restored = context.client.post(
        f"{path}/inventory/adjust",
        headers=headers,
        json={"delta": 11, "reason": "test_cleanup", "idempotency_key": uuid.uuid4().hex},
    )
    assert restored.status_code == 200 and restored.json()["quantity_after"] == 10
