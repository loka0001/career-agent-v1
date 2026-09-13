"""Product persistence and authoritative price/stock lookups."""

from __future__ import annotations

import builtins
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import InventoryTransactionModel, ProductModel, ProductVariantModel
from app.domain.enums import ProductStatus
from app.domain.errors import ConflictError, NotFoundError
from app.domain.models import ProductRecord, ProductUpdateInput


def to_product_record(row: ProductModel) -> ProductRecord:
    return ProductRecord(
        product_id=row.product_id,
        store_id=row.store_id,
        name=row.name,
        category=row.category,
        price=Decimal(row.price_numeric),
        stock=row.stock,
        features=list(row.features_json),
        customer_benefits=list(row.benefits_json),
        description=row.description,
        image_summary=row.image_summary,
        original_image_url=row.original_image_url,
        public_image_url=row.public_image_url,
        status=ProductStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
        sku=row.sku,
        currency=row.currency,
        compare_at_price=row.compare_at_price_numeric,
        stock_policy=row.stock_policy,
        images=list(row.images_json),
        tax=dict(row.tax_json),
        shipping_metadata=dict(row.shipping_json),
        source_of_truth=row.source_of_truth,
        source_provider=row.source_provider,
        version=row.version,
    )


class ProductRepository:
    def __init__(self, session: Session):
        self._session = session

    def list(self, store_id: str, *, active_only: bool = False) -> list[ProductRecord]:
        statement = select(ProductModel).where(ProductModel.store_id == store_id)
        if active_only:
            statement = statement.where(ProductModel.status == ProductStatus.ACTIVE.value)
        rows = self._session.scalars(statement.order_by(ProductModel.created_at.desc())).all()
        return [to_product_record(row) for row in rows]

    def categories(self, store_id: str) -> builtins.list[str]:
        statement = (
            select(ProductModel.category)
            .where(ProductModel.store_id == store_id)
            .distinct()
            .order_by(ProductModel.category)
        )
        return list(self._session.scalars(statement))

    def get_row(self, store_id: str, product_id: str) -> ProductModel:
        row = self._session.scalar(
            select(ProductModel).where(
                ProductModel.store_id == store_id,
                ProductModel.product_id == product_id,
            )
        )
        if row is None:
            raise NotFoundError(details={"entity": "product", "product_id": product_id})
        return row

    def get(self, store_id: str, product_id: str) -> ProductRecord:
        return to_product_record(self.get_row(store_id, product_id))

    def add(self, record: ProductRecord) -> ProductRecord:
        existing = self._session.scalar(
            select(ProductModel.id).where(
                ProductModel.store_id == record.store_id,
                ProductModel.product_id == record.product_id,
            )
        )
        if existing is not None:
            raise ConflictError(
                "Product ID already exists", details={"product_id": record.product_id}
            )
        row = ProductModel(
            store_id=record.store_id,
            product_id=record.product_id,
            name=record.name,
            category=record.category,
            sku=record.sku or record.product_id,
            currency=record.currency.upper(),
            price_numeric=record.price,
            compare_at_price_numeric=record.compare_at_price,
            stock=record.stock,
            stock_policy=record.stock_policy,
            images_json=record.images or [record.public_image_url or record.original_image_url],
            tax_json=record.tax,
            shipping_json=record.shipping_metadata,
            source_of_truth=record.source_of_truth,
            source_provider=record.source_provider,
            version=record.version,
            features_json=record.features,
            benefits_json=record.customer_benefits,
            description=record.description,
            image_summary=record.image_summary,
            original_image_url=record.original_image_url,
            public_image_url=record.public_image_url,
            status=record.status.value,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
        self._session.add(row)
        self._session.flush()
        variant = ProductVariantModel(
            store_id=record.store_id,
            product_pk=row.id,
            variant_id="default",
            title="Default",
            sku=row.sku,
            price_numeric=row.price_numeric,
            compare_at_price_numeric=row.compare_at_price_numeric,
            stock=row.stock,
            stock_policy=row.stock_policy,
            status="active",
        )
        self._session.add(variant)
        self._session.flush()
        if row.stock:
            self._session.add(
                InventoryTransactionModel(
                    store_id=record.store_id,
                    product_pk=row.id,
                    variant_pk=variant.id,
                    delta=row.stock,
                    quantity_before=0,
                    quantity_after=row.stock,
                    reason="initial_stock",
                    reference_type="product",
                    reference_id=row.product_id,
                    idempotency_key=f"product-create:{row.product_id}",
                )
            )
            self._session.flush()
        return to_product_record(row)

    def update(
        self,
        store_id: str,
        product_id: str,
        changes: ProductUpdateInput,
        *,
        mark_reviewed: bool = True,
    ) -> ProductRecord:
        row = self.get_row(store_id, product_id)
        values = changes.model_dump(exclude_none=True)
        requested_stock = values.pop("stock", None)
        authoritative_fields = {
            "price",
            "compare_at_price",
            "sku",
            "currency",
            "stock_policy",
        }
        if row.source_of_truth == "external" and (
            requested_stock is not None or authoritative_fields.intersection(values)
        ):
            raise ConflictError(
                "Externally managed price and inventory must be changed in the connected store",
                details={"provider": row.source_provider or "external"},
            )
        mapping = {
            "price": "price_numeric",
            "compare_at_price": "compare_at_price_numeric",
            "features": "features_json",
            "customer_benefits": "benefits_json",
            "tax": "tax_json",
            "shipping_metadata": "shipping_json",
        }
        for key, value in values.items():
            setattr(row, mapping.get(key, key), value)
        # The synthetic default variant is the orderable representation of a local product.
        # Keep its shared financial facts aligned; custom variants retain their own prices.
        default_variant = self._session.scalar(
            select(ProductVariantModel)
            .where(
                ProductVariantModel.store_id == store_id,
                ProductVariantModel.product_pk == row.id,
                ProductVariantModel.variant_id == "default",
            )
            .with_for_update()
        )
        if default_variant is not None and authoritative_fields.intersection(values):
            for key in ("price", "compare_at_price", "sku", "stock_policy"):
                if key in values:
                    setattr(default_variant, mapping.get(key, key), values[key])
            default_variant.version += 1
        if requested_stock is not None and requested_stock != row.stock:
            from app.services.inventory import adjust_inventory

            adjust_inventory(
                self._session,
                store_id=store_id,
                product_id=product_id,
                delta=requested_stock - row.stock,
                reason="manual_set",
                idempotency_key=f"product-patch:{product_id}:{uuid.uuid4().hex}",
                reference_type="product",
                reference_id=product_id,
            )
            row = self.get_row(store_id, product_id)
        row.currency = row.currency.upper()
        row.version += 1
        if mark_reviewed:
            row.status = ProductStatus.REVIEWED.value
        self._session.flush()
        return to_product_record(row)

    def activate(self, store_id: str, product_id: str) -> ProductRecord:
        row = self.get_row(store_id, product_id)
        if row.status not in {ProductStatus.REVIEWED.value, ProductStatus.ACTIVE.value}:
            raise ConflictError("Product must be reviewed before activation")
        row.status = ProductStatus.ACTIVE.value
        self._session.flush()
        return to_product_record(row)
