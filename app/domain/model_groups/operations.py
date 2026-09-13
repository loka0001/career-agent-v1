"""Generated operations slice of models.py."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from app.domain.enums import Language, MemberRole, Platform
from app.domain.model_groups.shared import ContractModel, MoneyModel


class PlanOut(MoneyModel):
    key: str
    name: str
    price: Decimal
    quotas: dict[str, int]
    features: list[str]


class SubscriptionOut(ContractModel):
    plan: PlanOut
    status: str
    provider: str
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool = False
    trial_end: datetime | None = None
    usage: dict[str, int]


class ChangePlanInput(ContractModel):
    plan_key: str = Field(pattern=r"^(starter|growth|pro)$")


class DeletionConfirmationInput(ContractModel):
    password: str = Field(min_length=8, max_length=256)
    confirmation: Literal["DELETE"]


class DeletionRequestOut(ContractModel):
    request_id: str
    scope: str
    status: str
    execute_after: datetime
    requested_at: datetime
    completed_at: datetime | None = None


class RetentionPolicyInput(ContractModel):
    message_days: int = Field(ge=30, le=2555)
    media_days: int = Field(ge=1, le=365)
    event_days: int = Field(ge=30, le=2555)


class RetentionPolicyOut(RetentionPolicyInput):
    store_id: str
    updated_at: datetime


class StoreSuspensionInput(ContractModel):
    suspended: bool
    reason: str = Field(min_length=3, max_length=500)


class TeamMemberOut(ContractModel):
    membership_id: int
    user_id: str
    email: str
    full_name: str
    role: MemberRole
    created_at: datetime


class TeamInviteInput(ContractModel):
    email: str = Field(
        min_length=5,
        max_length=320,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )
    full_name: str = Field(default="", max_length=160)
    role: MemberRole = MemberRole.AGENT


class TeamInviteResult(ContractModel):
    invite_id: str
    email: str
    role: MemberRole
    status: str
    expires_at: datetime


class TeamRoleUpdate(ContractModel):
    role: MemberRole


class StoreSettingsInput(ContractModel):
    store_name: str = Field(min_length=2, max_length=160)
    default_language: Language = Language.ARABIC
    business_type: str = Field(default="retail", min_length=2, max_length=80)
    logo_url: str | None = Field(default=None, max_length=2000)
    brand_colors: dict[str, str] = Field(default_factory=dict)
    tone: str = Field(default="friendly", min_length=2, max_length=40)
    assistant_name: str = Field(default="مساعد المتجر", min_length=2, max_length=100)
    assistant_instructions: str = Field(default="", max_length=4000)
    shipping_policy: str = Field(default="", max_length=6000)
    return_policy: str = Field(default="", max_length=6000)
    ai_monthly_budget: Decimal = Field(
        default=Decimal("25.00"),
        ge=0,
        le=Decimal("1000000.00"),
        max_digits=12,
        decimal_places=2,
    )


class StoreSettingsOut(StoreSettingsInput):
    store_id: str
    slug: str
    onboarding_steps: dict[str, bool] = Field(default_factory=dict)
    onboarding_completed: bool = False
    updated_at: datetime


class CategoryCount(ContractModel):
    category: str
    count: int


class DashboardProductStats(MoneyModel):
    total: int
    active: int
    in_review: int
    out_of_stock: int
    low_stock: int
    inventory_value: Decimal
    categories: list[CategoryCount]


class DashboardContentStats(ContractModel):
    total_packs: int
    approved: int
    published: int
    drafts: int


class DashboardPublishingStats(ContractModel):
    total: int
    succeeded: int
    failed: int
    facebook: int
    instagram: int


class DashboardRecentPublication(ContractModel):
    publication_id: int
    product_name: str
    platform: Platform
    success: bool
    permalink: str | None = None
    attempted_at: datetime


class DashboardRecentQuery(ContractModel):
    id: int
    message: str
    intent: str
    recommendation_count: int
    created_at: datetime


class DashboardLowStockProduct(MoneyModel):
    product_id: str
    name: str
    stock: int
    price: Decimal
    image_url: str


class DashboardSalesStats(ContractModel):
    total_queries: int
    answered_with_recommendations: int
    recent: list[DashboardRecentQuery]


class DashboardSnapshot(ContractModel):
    products: DashboardProductStats
    content: DashboardContentStats
    publishing: DashboardPublishingStats
    sales: DashboardSalesStats
    low_stock_products: list[DashboardLowStockProduct]
    recent_publications: list[DashboardRecentPublication]
    generated_at: datetime
