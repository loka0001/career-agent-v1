"""Generated orders slice of models.py."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.model_groups.shared import utc_now


class OrderModel(Base):
    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("store_id", "idempotency_key", name="uq_order_idempotency"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    conversation_id: Mapped[int | None] = mapped_column(
        ForeignKey("conversations.id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    payment_status: Mapped[str] = mapped_column(String(20), default="unpaid", index=True)
    fulfillment_status: Mapped[str] = mapped_column(String(20), default="unfulfilled", index=True)
    currency: Mapped[str] = mapped_column(String(3), default="EGP")
    subtotal_numeric: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    discount_numeric: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    shipping_total_numeric: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    tax_total_numeric: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    total_numeric: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    shipping_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    provider_references_json: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    idempotency_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    inventory_reserved: Mapped[bool] = mapped_column(default=False)
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class OrderItemModel(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    product_pk: Mapped[int] = mapped_column(ForeignKey("products.id"))
    variant_pk: Mapped[int | None] = mapped_column(ForeignKey("product_variants.id"), nullable=True)
    product_id: Mapped[str] = mapped_column(String(64))
    variant_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sku: Mapped[str] = mapped_column(String(100), default="")
    options_json: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    product_name: Mapped[str] = mapped_column(String(160))
    unit_price_numeric: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    quantity: Mapped[int]
    line_total_numeric: Mapped[Decimal] = mapped_column(Numeric(12, 2))


class OrderTransitionModel(Base):
    __tablename__ = "order_transitions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str] = mapped_column(String(20))
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reason: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ExternalOrderMappingModel(Base):
    __tablename__ = "external_order_mappings"
    __table_args__ = (
        UniqueConstraint(
            "provider_connection_id",
            "external_order_id",
            name="uq_external_order",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    provider_connection_id: Mapped[str] = mapped_column(
        ForeignKey("provider_connections.id"), index=True
    )
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    external_order_id: Mapped[str] = mapped_column(String(255), index=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    payload_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
