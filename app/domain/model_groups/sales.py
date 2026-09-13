"""Generated sales slice of models.py."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.domain.enums import ChannelMode, ChannelType, CustomerIntent, Language
from app.domain.model_groups.catalog import ProductRecord
from app.domain.model_groups.shared import ContractModel, MoneyModel


class CustomerNeed(MoneyModel):
    intent: CustomerIntent
    categories: list[str] = Field(default_factory=list)
    max_budget: Decimal | None = Field(default=None, gt=0)
    required_features: list[str] = Field(default_factory=list)
    use_cases: list[str] = Field(default_factory=list)
    excluded_features: list[str] = Field(default_factory=list)
    language: Language = Language.ARABIC


class Recommendation(ContractModel):
    product_id: str
    score: float = Field(ge=0, le=1)
    reasons: list[str]
    product: ProductRecord


class GroundedReply(ContractModel):
    reply: str = Field(min_length=1, max_length=5000)
    cited_product_ids: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)


class SalesAssistantResponse(ContractModel):
    need: CustomerNeed
    recommendations: list[Recommendation] = Field(max_length=3)
    reply: str
    citations: list[str]
    insufficient_context: bool


class PolicyExcerpt(ContractModel):
    source_ref: str
    title: str
    body: str
    score: float = Field(ge=0, le=1)


class IntegrationStatus(ContractModel):
    name: str
    configured: bool
    mode: str
    masked_identifier: str | None = None
    last_check: datetime | None = None


class SendResult(ContractModel):
    """Outcome of delivering one outbound message through a channel adapter."""

    success: bool
    external_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None


class ChannelSummary(ContractModel):
    id: int
    channel_type: ChannelType
    mode: ChannelMode
    display_name: str
    is_active: bool
    configured: bool


class CustomerSummary(ContractModel):
    id: int
    display_name: str
    phone: str | None = None
    email: str | None = None
    tags: list[str] = Field(default_factory=list)
    lead_score: int = 0
    consent: dict[str, bool] = Field(default_factory=dict)
    first_seen_at: datetime
    last_seen_at: datetime
