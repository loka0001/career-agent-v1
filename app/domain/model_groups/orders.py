"""Generated orders slice of models.py."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.domain.enums import OrderStatus
from app.domain.model_groups.shared import ContractModel, MoneyModel


class OrderItemInput(ContractModel):
    product_id: str = Field(min_length=1, max_length=64)
    variant_id: str | None = Field(default=None, min_length=1, max_length=64)
    quantity: int = Field(ge=1, le=1000)


class DraftOrderInput(MoneyModel):
    conversation_id: int = Field(gt=0)
    items: list[OrderItemInput] = Field(min_length=1, max_length=100)
    discount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    shipping_total: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    tax_total: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="EGP", min_length=3, max_length=3)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=160)
    shipping: dict[str, str] = Field(default_factory=dict)
    notes: str = Field(default="", max_length=2000)


class OrderTransitionInput(ContractModel):
    status: OrderStatus
    reason: str = Field(default="", max_length=500)
    notify_customer: bool = False


class OrderItemOut(MoneyModel):
    product_id: str
    variant_id: str | None = None
    sku: str = ""
    options: dict[str, str] = Field(default_factory=dict)
    product_name: str
    unit_price: Decimal
    quantity: int
    line_total: Decimal


class OrderTimelineEntry(ContractModel):
    from_status: OrderStatus | None = None
    to_status: OrderStatus
    actor_user_id: str | None = None
    reason: str
    created_at: datetime


class OrderOut(MoneyModel):
    id: int
    customer_id: int
    conversation_id: int | None = None
    status: OrderStatus
    currency: str
    subtotal: Decimal
    discount: Decimal
    shipping_total: Decimal = Decimal("0")
    tax_total: Decimal = Decimal("0")
    total: Decimal
    shipping: dict[str, str]
    notes: str
    payment_provider: str | None = None
    payment_status: str | None = None
    fulfillment_status: str = "unfulfilled"
    provider_references: dict[str, str] = Field(default_factory=dict)
    idempotency_key: str | None = None
    refunded_amount: Decimal = Decimal("0")
    items: list[OrderItemOut]
    timeline: list[OrderTimelineEntry]
    created_at: datetime
    updated_at: datetime


class CheckoutLink(ContractModel):
    provider: str
    url: str
    expires_at: datetime
