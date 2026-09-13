"""Generated catalog slice of models.py."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.model_groups.shared import utc_now

if TYPE_CHECKING:
    from app.db.model_groups.content import MarketingPackModel


class ProductModel(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("store_id", "product_id", name="uq_product_store_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    product_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(100), index=True)
    sku: Mapped[str] = mapped_column(String(100), default="", index=True)
    currency: Mapped[str] = mapped_column(String(3), default="EGP")
    price_numeric: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    compare_at_price_numeric: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    stock: Mapped[int]
    stock_policy: Mapped[str] = mapped_column(String(20), default="deny")
    images_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    tax_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    shipping_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    source_of_truth: Mapped[str] = mapped_column(String(20), default="local", index=True)
    source_provider: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    version: Mapped[int] = mapped_column(default=1)
    features_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    benefits_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    description: Mapped[str] = mapped_column(Text)
    image_summary: Mapped[str] = mapped_column(Text, default="")
    original_image_url: Mapped[str] = mapped_column(Text)
    public_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    marketing_packs: Mapped[list[MarketingPackModel]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    variants: Mapped[list[ProductVariantModel]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


class ProductVariantModel(Base):
    __tablename__ = "product_variants"
    __table_args__ = (
        UniqueConstraint("product_pk", "variant_id", name="uq_product_variant_id"),
        UniqueConstraint("store_id", "sku", name="uq_variant_store_sku"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    product_pk: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    variant_id: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(160), default="Default")
    sku: Mapped[str] = mapped_column(String(100), index=True)
    options_json: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    price_numeric: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    compare_at_price_numeric: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    stock: Mapped[int] = mapped_column(default=0)
    stock_policy: Mapped[str] = mapped_column(String(20), default="deny")
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    product: Mapped[ProductModel] = relationship(back_populates="variants")


class InventoryTransactionModel(Base):
    __tablename__ = "inventory_transactions"
    __table_args__ = (
        UniqueConstraint("store_id", "idempotency_key", name="uq_inventory_idempotency"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    product_pk: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    variant_pk: Mapped[int | None] = mapped_column(
        ForeignKey("product_variants.id"), nullable=True, index=True
    )
    delta: Mapped[int]
    quantity_before: Mapped[int]
    quantity_after: Mapped[int]
    reason: Mapped[str] = mapped_column(String(80), index=True)
    reference_type: Mapped[str] = mapped_column(String(40), default="")
    reference_id: Mapped[str] = mapped_column(String(100), default="", index=True)
    idempotency_key: Mapped[str] = mapped_column(String(160))
    actor_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ExternalProductMappingModel(Base):
    __tablename__ = "external_product_mappings"
    __table_args__ = (
        UniqueConstraint(
            "provider_connection_id",
            "external_product_id",
            "external_variant_id",
            name="uq_external_product_variant",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    provider_connection_id: Mapped[str] = mapped_column(
        ForeignKey("provider_connections.id"), index=True
    )
    product_pk: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    external_product_id: Mapped[str] = mapped_column(String(255), index=True)
    external_variant_id: Mapped[str] = mapped_column(String(255), default="")
    external_sku: Mapped[str] = mapped_column(String(255), default="", index=True)
    external_inventory_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    payload_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
