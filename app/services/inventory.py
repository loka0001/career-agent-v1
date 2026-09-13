"""Atomic, idempotent inventory adjustments with a complete audit ledger."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import (
    InventoryTransactionModel,
    ProductModel,
    ProductVariantModel,
)
from app.domain.errors import ConflictError, NotFoundError
from app.domain.models import InventoryTransactionOut, ProductVariantInput, ProductVariantOut


def _variant_out(row: ProductVariantModel) -> ProductVariantOut:
    return ProductVariantOut(
        id=row.id,
        variant_id=row.variant_id,
        title=row.title,
        sku=row.sku,
        options=dict(row.options_json),
        price=row.price_numeric,
        compare_at_price=row.compare_at_price_numeric,
        stock=row.stock,
        stock_policy=row.stock_policy,
        status=row.status,
        version=row.version,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def list_variants(session: Session, store_id: str, product_id: str) -> list[ProductVariantOut]:
    product = session.scalar(
        select(ProductModel).where(
            ProductModel.store_id == store_id,
            ProductModel.product_id == product_id,
        )
    )
    if product is None:
        raise NotFoundError(details={"entity": "product", "product_id": product_id})
    rows = session.scalars(
        select(ProductVariantModel)
        .where(
            ProductVariantModel.store_id == store_id,
            ProductVariantModel.product_pk == product.id,
        )
        .order_by(ProductVariantModel.id)
    ).all()
    return [_variant_out(row) for row in rows]


def add_variant(
    session: Session,
    store_id: str,
    product_id: str,
    payload: ProductVariantInput,
    *,
    actor_user_id: str | None = None,
) -> ProductVariantOut:
    product = session.scalar(
        select(ProductModel)
        .where(
            ProductModel.store_id == store_id,
            ProductModel.product_id == product_id,
        )
        .with_for_update()
    )
    if product is None:
        raise NotFoundError(details={"entity": "product", "product_id": product_id})
    if product.source_of_truth == "external":
        raise ConflictError(
            "Externally managed variants must be changed in the connected store",
            details={"provider": product.source_provider or "external"},
        )
    row = ProductVariantModel(
        store_id=store_id,
        product_pk=product.id,
        variant_id=payload.variant_id,
        title=payload.title.strip(),
        sku=payload.sku.strip(),
        options_json=payload.options,
        price_numeric=payload.price,
        compare_at_price_numeric=payload.compare_at_price,
        stock=payload.stock,
        stock_policy=payload.stock_policy,
        status="active",
    )
    try:
        with session.begin_nested():
            session.add(row)
            session.flush()
    except IntegrityError as exc:
        raise ConflictError(
            "Variant ID or SKU already exists",
            details={"variant_id": payload.variant_id, "sku": payload.sku},
        ) from exc
    session.add(
        InventoryTransactionModel(
            store_id=store_id,
            product_pk=product.id,
            variant_pk=row.id,
            delta=payload.stock,
            quantity_before=0,
            quantity_after=payload.stock,
            reason="variant_created",
            reference_type="variant",
            reference_id=row.variant_id,
            idempotency_key=f"variant-create:{row.id}",
            actor_user_id=actor_user_id,
        )
    )
    _sync_product_stock(session, product)
    session.flush()
    return _variant_out(row)


def _sync_product_stock(session: Session, product: ProductModel) -> None:
    variants = session.scalars(
        select(ProductVariantModel).where(
            ProductVariantModel.store_id == product.store_id,
            ProductVariantModel.product_pk == product.id,
            ProductVariantModel.status == "active",
        )
    ).all()
    if variants:
        product.stock = sum(row.stock for row in variants)
        product.version += 1
        product.updated_at = datetime.now(UTC)


def adjust_inventory(
    session: Session,
    *,
    store_id: str,
    product_id: str,
    delta: int,
    reason: str,
    idempotency_key: str,
    actor_user_id: str | None = None,
    variant_id: str | None = None,
    allow_negative: bool = False,
    reference_type: str = "",
    reference_id: str = "",
    require_local: bool = False,
) -> InventoryTransactionOut:
    product = session.scalar(
        select(ProductModel)
        .where(
            ProductModel.store_id == store_id,
            ProductModel.product_id == product_id,
        )
        .with_for_update()
    )
    if product is None:
        raise NotFoundError(details={"entity": "product", "product_id": product_id})
    if require_local and product.source_of_truth == "external":
        raise ConflictError(
            "Externally managed stock must be changed in the connected store",
            details={"provider": product.source_provider or "external"},
        )

    def replay(existing: InventoryTransactionModel) -> InventoryTransactionOut:
        result = _transaction_out(session, existing)
        if (
            result.product_id != product_id
            or (variant_id is not None and result.variant_id != variant_id)
            or result.delta != delta
            or result.reason != reason
            or result.reference_type != reference_type
            or result.reference_id != reference_id
            or result.actor_user_id != actor_user_id
        ):
            raise ConflictError(
                "Idempotency key belongs to a different inventory adjustment",
                details={"field": "idempotency_key"},
            )
        return result

    existing = session.scalar(
        select(InventoryTransactionModel).where(
            InventoryTransactionModel.store_id == store_id,
            InventoryTransactionModel.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        return replay(existing)

    variant: ProductVariantModel | None = None
    if variant_id is None:
        variants = session.scalars(
            select(ProductVariantModel)
            .where(
                ProductVariantModel.store_id == store_id,
                ProductVariantModel.product_pk == product.id,
                ProductVariantModel.status == "active",
            )
            .order_by(ProductVariantModel.id)
            .with_for_update()
        ).all()
        if len(variants) == 1:
            variant = variants[0]
        elif len(variants) > 1:
            raise ConflictError(
                "A variant is required for products with multiple variants",
                details={"product_id": product_id},
            )
    else:
        variant = session.scalar(
            select(ProductVariantModel)
            .where(
                ProductVariantModel.store_id == store_id,
                ProductVariantModel.product_pk == product.id,
                ProductVariantModel.variant_id == variant_id,
            )
            .with_for_update()
        )
        if variant is None:
            raise NotFoundError(details={"entity": "variant", "variant_id": variant_id})

    # Re-check after locking inventory so concurrent retries cannot both apply the delta.
    existing = session.scalar(
        select(InventoryTransactionModel).where(
            InventoryTransactionModel.store_id == store_id,
            InventoryTransactionModel.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        return replay(existing)

    target = variant if variant is not None else product
    before = target.stock
    after = before + delta
    can_continue = getattr(target, "stock_policy", "deny") == "continue"
    if after < 0 and not (allow_negative or can_continue):
        raise ConflictError(
            "Inventory cannot become negative",
            details={"product_id": product_id, "available": before, "requested_delta": delta},
        )
    target_model = ProductVariantModel if variant is not None else ProductModel
    target_id = target.id
    now = datetime.now(UTC)
    stock_guard = [target_model.id == target_id, target_model.stock == before]
    if after < 0 and not (allow_negative or can_continue):
        stock_guard.append(target_model.stock + delta >= 0)

    try:
        with session.begin_nested():
            changed = cast(
                CursorResult[object],
                session.execute(
                    update(target_model)
                    .where(*stock_guard)
                    .values(
                        stock=after,
                        version=target_model.version + 1,
                        updated_at=now,
                    )
                    .execution_options(synchronize_session=False)
                ),
            )
            if changed.rowcount != 1:
                session.refresh(target)
                raise ConflictError(
                    "Inventory changed concurrently; retry the adjustment",
                    details={
                        "product_id": product_id,
                        "available": target.stock,
                        "requested_delta": delta,
                    },
                )
            session.refresh(target)
            if variant is not None:
                _sync_product_stock(session, product)
            transaction = InventoryTransactionModel(
                store_id=store_id,
                product_pk=product.id,
                variant_pk=variant.id if variant is not None else None,
                delta=delta,
                quantity_before=before,
                quantity_after=after,
                reason=reason,
                reference_type=reference_type,
                reference_id=reference_id,
                idempotency_key=idempotency_key,
                actor_user_id=actor_user_id,
            )
            session.add(transaction)
            session.flush()
    except IntegrityError:
        existing = session.scalar(
            select(InventoryTransactionModel).where(
                InventoryTransactionModel.store_id == store_id,
                InventoryTransactionModel.idempotency_key == idempotency_key,
            )
        )
        if existing is None:
            raise
        session.refresh(product)
        if variant is not None:
            session.refresh(variant)
        return replay(existing)
    return _transaction_out(session, transaction)


def list_inventory_transactions(
    session: Session,
    store_id: str,
    product_id: str,
    *,
    limit: int = 100,
) -> list[InventoryTransactionOut]:
    product = session.scalar(
        select(ProductModel).where(
            ProductModel.store_id == store_id,
            ProductModel.product_id == product_id,
        )
    )
    if product is None:
        raise NotFoundError(details={"entity": "product", "product_id": product_id})
    rows = session.scalars(
        select(InventoryTransactionModel)
        .where(
            InventoryTransactionModel.store_id == store_id,
            InventoryTransactionModel.product_pk == product.id,
        )
        .order_by(InventoryTransactionModel.id.desc())
        .limit(limit)
    ).all()
    return [_transaction_out(session, row, product_id=product_id) for row in rows]


def _transaction_out(
    session: Session,
    row: InventoryTransactionModel,
    *,
    product_id: str | None = None,
) -> InventoryTransactionOut:
    product = session.get(ProductModel, row.product_pk)
    variant = session.get(ProductVariantModel, row.variant_pk) if row.variant_pk else None
    return InventoryTransactionOut(
        id=row.id,
        product_id=product_id or (product.product_id if product is not None else ""),
        variant_id=variant.variant_id if variant is not None else None,
        delta=row.delta,
        quantity_before=row.quantity_before,
        quantity_after=row.quantity_after,
        reason=row.reason,
        reference_type=row.reference_type,
        reference_id=row.reference_id,
        idempotency_key=row.idempotency_key,
        actor_user_id=row.actor_user_id,
        created_at=row.created_at,
    )
