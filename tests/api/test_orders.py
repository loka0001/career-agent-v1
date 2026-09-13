from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from sqlalchemy import select

from app.db.models import ConversationModel, ProductModel


def _conversation_id(context) -> int:
    with context.session_factory() as session:
        conversation_id = session.scalar(
            select(ConversationModel.id)
            .where(ConversationModel.store_id == "demo-store")
            .order_by(ConversationModel.id)
        )
        assert conversation_id is not None
        return conversation_id


def test_order_from_conversation_checkout_and_timeline(authenticated) -> None:
    context, headers = authenticated
    created = context.client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "conversation_id": _conversation_id(context),
            "items": [{"product_id": "A101", "quantity": 2}],
            "discount": "100.00",
            "shipping": {
                "name": "منى عادل",
                "phone": "201000000000",
                "city": "Cairo",
                "address": "Demo address",
            },
            "notes": "اتصال قبل التوصيل",
        },
    )
    assert created.status_code == 201, created.text
    order = created.json()
    assert order["status"] == "draft"
    assert order["subtotal"] == "2598.00"
    assert order["total"] == "2498.00"
    assert order["timeline"][0]["to_status"] == "draft"

    invalid = context.client.post(
        f"/api/v1/orders/{order['id']}/transition",
        headers=headers,
        json={"status": "shipped", "reason": "skip"},
    )
    assert invalid.status_code == 409
    assert invalid.json()["error"]["details"] == {"from": "draft", "to": "shipped"}

    checkout = context.client.post(
        f"/api/v1/orders/{order['id']}/checkout", headers=headers
    )
    assert checkout.status_code == 200, checkout.text
    checkout_url = checkout.json()["url"]
    token = parse_qs(urlparse(checkout_url).query)["token"][0]
    page = context.client.get(f"/checkout/demo/{order['id']}", params={"token": token})
    assert page.status_code == 200
    assert "لا تخصم أي أموال حقيقية" in page.text

    paid = context.client.post(
        f"/checkout/demo/{order['id']}", data={"token": token}
    )
    assert paid.status_code == 200
    detail = context.client.get(f"/api/v1/orders/{order['id']}", headers=headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["status"] == "paid"
    assert [entry["to_status"] for entry in body["timeline"]] == [
        "draft",
        "pending",
        "confirmed",
        "paid",
    ]


def test_order_rejects_unavailable_quantity_and_cross_store_id(authenticated) -> None:
    context, headers = authenticated
    unavailable = context.client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "conversation_id": _conversation_id(context),
            "items": [{"product_id": "A101", "quantity": 999}],
            "discount": "0",
            "shipping": {},
        },
    )
    assert unavailable.status_code == 409

    missing = context.client.get("/api/v1/orders/999999", headers=headers)
    assert missing.status_code == 404


def test_pending_order_reserves_stock_and_cancellation_releases_it(authenticated) -> None:
    context, headers = authenticated
    with context.session_factory() as session:
        before = session.scalar(
            select(ProductModel.stock).where(
                ProductModel.store_id == "demo-store",
                ProductModel.product_id == "A102",
            )
        )
    assert before is not None and before >= 1
    created = context.client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "conversation_id": _conversation_id(context),
            "items": [{"product_id": "A102", "quantity": 1}],
            "discount": "0",
            "shipping": {},
        },
    )
    assert created.status_code == 201, created.text
    order_id = created.json()["id"]
    pending = context.client.post(
        f"/api/v1/orders/{order_id}/transition",
        headers=headers,
        json={"status": "pending", "reason": "reserve"},
    )
    assert pending.status_code == 200, pending.text
    with context.session_factory() as session:
        reserved = session.scalar(
            select(ProductModel.stock).where(
                ProductModel.store_id == "demo-store",
                ProductModel.product_id == "A102",
            )
        )
    assert reserved == before - 1
    cancelled = context.client.post(
        f"/api/v1/orders/{order_id}/transition",
        headers=headers,
        json={"status": "cancelled", "reason": "customer_request"},
    )
    assert cancelled.status_code == 200, cancelled.text
    with context.session_factory() as session:
        restored = session.scalar(
            select(ProductModel.stock).where(
                ProductModel.store_id == "demo-store",
                ProductModel.product_id == "A102",
            )
        )
    assert restored == before


def test_cod_checkout_confirms_and_cancellation_closes_payment(context) -> None:
    from app.domain.enums import OrderStatus
    from app.domain.models import DraftOrderInput
    from app.integrations.payments import CodPaymentProvider
    from app.services.orders import (
        create_draft_order,
        create_order_checkout,
        order_out,
        transition_order,
    )

    with context.session_factory.begin() as session:
        conversation_id = _conversation_id(context)
        order = create_draft_order(
            session,
            "demo-store",
            None,
            DraftOrderInput(
                conversation_id=conversation_id,
                items=[{"product_id": "A103", "quantity": 1}],
                discount="0",
                shipping={},
            ),
        )
        create_order_checkout(
            session,
            "demo-store",
            order.id,
            None,
            "https://example.com",
            "test-secret",
            CodPaymentProvider(),
        )
        confirmed = order_out(session, "demo-store", order.id)
        assert confirmed.status.value == "confirmed"
        assert confirmed.payment_status == "awaiting_cash"
        cancelled = transition_order(
            session,
            "demo-store",
            order.id,
            OrderStatus.CANCELLED,
            actor_user_id=None,
            reason="test_cleanup",
        )
        assert cancelled.status.value == "cancelled"
        assert cancelled.payment_status == "cancelled"
