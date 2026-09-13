"""Generated catalog slice of models.py."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import Field

from app.domain.enums import ProductStatus
from app.domain.model_groups.shared import ContractModel, MoneyModel


class ProductCreateInput(MoneyModel):
    product_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=160)
    category: str = Field(min_length=1, max_length=100)
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    stock: int = Field(ge=0, le=1_000_000)
    raw_features: list[str] = Field(default_factory=list, max_length=30)
    sku: str | None = Field(default=None, min_length=1, max_length=100)
    currency: str = Field(default="EGP", min_length=3, max_length=3)
    compare_at_price: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    stock_policy: Literal["deny", "continue"] = "deny"


class ImageAnalysis(ContractModel):
    product_type: str | None = None
    colors: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    visible_features: list[str] = Field(default_factory=list)
    image_summary: str = Field(default="", max_length=1000)
    confidence_notes: list[str] = Field(default_factory=list)


class ProductCopy(ContractModel):
    customer_benefits: list[str] = Field(default_factory=list, max_length=8)
    description: str = Field(min_length=1, max_length=2000)


class ProductRecord(MoneyModel):
    product_id: str
    store_id: str
    name: str
    category: str
    price: Decimal
    stock: int
    features: list[str]
    customer_benefits: list[str]
    description: str
    image_summary: str
    original_image_url: str
    public_image_url: str | None = None
    status: ProductStatus
    created_at: datetime
    updated_at: datetime
    sku: str = ""
    currency: str = "EGP"
    compare_at_price: Decimal | None = None
    stock_policy: Literal["deny", "continue"] = "deny"
    images: list[str] = Field(default_factory=list)
    tax: dict[str, Any] = Field(default_factory=dict)
    shipping_metadata: dict[str, Any] = Field(default_factory=dict)
    source_of_truth: Literal["local", "external"] = "local"
    source_provider: str | None = None
    version: int = 1


class ProductUpdateInput(MoneyModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    price: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    stock: int | None = Field(default=None, ge=0, le=1_000_000)
    features: list[str] | None = Field(default=None, max_length=30)
    customer_benefits: list[str] | None = Field(default=None, max_length=8)
    description: str | None = Field(default=None, min_length=1, max_length=2000)
    sku: str | None = Field(default=None, min_length=1, max_length=100)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    compare_at_price: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    stock_policy: Literal["deny", "continue"] | None = None
    tax: dict[str, Any] | None = None
    shipping_metadata: dict[str, Any] | None = None


class ProductVariantInput(MoneyModel):
    variant_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    title: str = Field(min_length=1, max_length=160)
    sku: str = Field(min_length=1, max_length=100)
    options: dict[str, str] = Field(default_factory=dict)
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    compare_at_price: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    stock: int = Field(default=0, ge=0, le=1_000_000)
    stock_policy: Literal["deny", "continue"] = "deny"


class ProductVariantOut(ProductVariantInput):
    # Persisted quantities may exceed creation limits or be negative under backorder policy.
    stock: int = 0
    id: int
    status: str
    version: int
    created_at: datetime
    updated_at: datetime


class InventoryAdjustmentInput(ContractModel):
    delta: int = Field(ge=-1_000_000, le=1_000_000)
    reason: str = Field(min_length=1, max_length=80)
    idempotency_key: str = Field(min_length=8, max_length=160)
    variant_id: str | None = Field(default=None, min_length=1, max_length=64)
    allow_negative: bool = False
    reference_type: str = Field(default="manual", max_length=40)
    reference_id: str = Field(default="", max_length=100)


class InventoryTransactionOut(ContractModel):
    id: int
    product_id: str
    variant_id: str | None = None
    delta: int
    quantity_before: int
    quantity_after: int
    reason: str
    reference_type: str
    reference_id: str
    idempotency_key: str
    actor_user_id: str | None = None
    created_at: datetime
