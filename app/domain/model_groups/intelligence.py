"""Generated intelligence slice of models.py."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.domain.enums import OpportunityStatus
from app.domain.model_groups.sales import CustomerSummary
from app.domain.model_groups.shared import ContractModel, MoneyModel


class ScoreSignal(ContractModel):
    name: str
    value: int
    weight: int
    contribution: int
    explanation: str


class RfmSnapshot(MoneyModel):
    recency_days: int
    frequency: int
    monetary: Decimal
    recency_score: int = Field(ge=1, le=5)
    frequency_score: int = Field(ge=1, le=5)
    monetary_score: int = Field(ge=1, le=5)


class CustomerTimelineEvent(ContractModel):
    event_type: str
    title: str
    detail: str
    occurred_at: datetime


class CustomerIntelligence(MoneyModel):
    customer: CustomerSummary
    lead_score: int
    score_signals: list[ScoreSignal]
    segments: list[str]
    completed_orders: int
    total_revenue: Decimal
    average_order_value: Decimal
    days_since_last_activity: int
    preferred_product_ids: list[str]
    rfm: RfmSnapshot
    purchase_probability: int = Field(ge=0, le=100)
    churn_risk: str
    timeline: list[CustomerTimelineEvent] = Field(default_factory=list)


class CustomerMergeInput(ContractModel):
    source_customer_id: int = Field(gt=0)


class OpportunityOut(MoneyModel):
    id: int
    opportunity_type: str
    customer_id: int | None = None
    related_product_ids: list[str]
    reason: str
    expected_revenue: Decimal
    realized_revenue: Decimal
    confidence: int
    suggested_action: str
    channel: str | None = None
    message: str
    status: OpportunityStatus
    detected_at: datetime


class OpportunityDashboard(MoneyModel):
    potential_revenue: Decimal
    recovered_revenue: Decimal
    new_count: int
    awaiting_approval_count: int
    executed_count: int
    won_count: int
    funnel: dict[str, int]
    top_opportunities: list[OpportunityOut]


class OpportunityDecisionInput(ContractModel):
    decision: str = Field(pattern=r"^(approve|execute|reject|won)$")
    realized_revenue: Decimal = Field(default=Decimal("0"), ge=0)
