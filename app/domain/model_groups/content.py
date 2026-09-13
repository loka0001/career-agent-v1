"""Generated content slice of models.py."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from pydantic import Field, field_validator

from app.domain.enums import Platform
from app.domain.model_groups.shared import ContractModel, MoneyModel


class BrandProfileInput(ContractModel):
    tone: str = Field(default="friendly", min_length=1, max_length=80)
    audience: str = Field(default="", max_length=2000)
    guidelines: str = Field(default="", max_length=4000)
    primary_color: str = Field(default="#6366f1", pattern=r"^#[0-9A-Fa-f]{6}$")


class BrandProfileOut(BrandProfileInput):
    updated_at: datetime


class ScheduledContentContract(ContractModel):
    scheduled_for: datetime | None = None

    @field_validator("scheduled_for")
    @classmethod
    def normalize_schedule(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        # Legacy naive timestamps are UTC, never the server's local timezone.
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class ContentGenerateInput(ScheduledContentContract):
    product_id: str = Field(min_length=1, max_length=64)
    content_format: str = Field(
        pattern=r"^(sales_post|educational_post|story_sequence|carousel|reel_script|limited_offer|comparison|faq)$"
    )
    platform: Platform
    tone: str = Field(default="", max_length=80)
    scheduled_for: datetime | None = None


class ContentItemUpdateInput(ScheduledContentContract):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    body: str | None = Field(default=None, min_length=1, max_length=8000)
    caption: str | None = Field(default=None, min_length=1, max_length=4000)
    hashtags: list[str] | None = Field(default=None, max_length=30)
    cta: str | None = Field(default=None, min_length=1, max_length=300)
    scheduled_for: datetime | None = None


class ContentItemOut(ScheduledContentContract):
    id: int
    campaign_id: int | None = None
    product_id: str
    content_format: str
    platform: Platform
    tone: str
    title: str
    body: str
    caption: str
    hashtags: list[str]
    cta: str
    validation_warnings: list[str]
    status: str
    current_version: int
    scheduled_for: datetime | None = None
    published_at: datetime | None = None
    external_id: str | None = None
    approved_at: datetime | None = None
    approved_by: str | None = None
    approved_by_user_id: str | None = None
    created_at: datetime
    updated_at: datetime


class ContentVersionOut(ContractModel):
    version: int
    snapshot: dict[str, Any]
    created_by_user_id: str | None = None
    created_at: datetime


class ContentRegenerateInput(ContractModel):
    section: str = Field(pattern=r"^(title|body|caption|hashtags|cta)$")


class CampaignGenerateInput(MoneyModel):
    name: str = Field(min_length=1, max_length=160)
    goal: str = Field(min_length=1, max_length=160)
    budget: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    product_ids: list[str] = Field(min_length=1, max_length=20)
    audience: str = Field(default="", max_length=2000)
    offer: str = Field(default="", max_length=2000)


class CampaignOut(MoneyModel):
    id: int
    name: str
    goal: str
    budget: Decimal
    product_ids: list[str]
    concept: str
    audience: str
    offer: str
    landing_copy: str
    whatsapp_template: str
    kpis: list[str]
    status: str
    created_at: datetime


class AnalyticsProductMetric(MoneyModel):
    product_id: str
    name: str
    quantity: int
    revenue: Decimal


class AnalyticsAgentMetric(ContractModel):
    user_id: str
    messages_sent: int


class AnalyticsSnapshot(MoneyModel):
    period_start: datetime
    period_end: datetime
    channel: str | None = None
    conversation_volume: int
    first_response_minutes: Decimal | None = None
    resolution_minutes: Decimal | None = None
    leads: int
    conversion_rate: Decimal
    attributed_revenue: Decimal
    recovered_revenue: Decimal
    orders_by_channel: dict[str, int]
    top_products: list[AnalyticsProductMetric]
    content_published: int
    content_engagements: int
    automation_runs: int
    automation_success_rate: Decimal
    ai_operations: int
    ai_cost: Decimal | None = None
    agent_performance: list[AnalyticsAgentMetric]
    funnel: dict[str, int]
