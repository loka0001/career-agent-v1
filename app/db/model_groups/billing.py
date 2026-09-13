"""Generated billing slice of models.py."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.model_groups.shared import utc_now


class AIUsageRecordModel(Base):
    __tablename__ = "ai_usage_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    operation: Mapped[str] = mapped_column(String(80), index=True)
    provider: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(120))
    input_tokens: Mapped[int | None] = mapped_column(nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(nullable=True)
    cost_numeric: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(nullable=True)
    cost_source: Mapped[str] = mapped_column(String(20), default="unknown")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )


class PlanModel(Base):
    __tablename__ = "plans"

    key: Mapped[str] = mapped_column(String(30), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    price_numeric: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    quotas_json: Mapped[dict[str, int]] = mapped_column(JSON)
    features_json: Mapped[list[str]] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(default=True)


class SubscriptionModel(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), unique=True, index=True
    )
    plan_key: Mapped[str] = mapped_column(ForeignKey("plans.key"))
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)
    provider: Mapped[str] = mapped_column(String(30), default="demo")
    provider_customer_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    provider_subscription_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(default=False)
    trial_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_provider_event_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class StripeEventModel(Base):
    __tablename__ = "stripe_events"
    __table_args__ = (UniqueConstraint("scope", "event_id", name="uq_stripe_event_scope_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scope: Mapped[str] = mapped_column(String(30), index=True)
    event_id: Mapped[str] = mapped_column(String(255))
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    livemode: Mapped[bool] = mapped_column(default=False)
    account_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class PaymentTransactionModel(Base):
    __tablename__ = "payment_transactions"
    __table_args__ = (UniqueConstraint("checkout_session_id", name="uq_payment_checkout_session"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    provider: Mapped[str] = mapped_column(String(30), index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    checkout_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    checkout_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_intent_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    amount_numeric: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    refunded_amount_numeric: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(3))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_provider_event_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class UsageRecordModel(Base):
    __tablename__ = "usage_records"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "store_id",
            "metric",
            "period_key",
            name="uq_usage_period_metric",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    metric: Mapped[str] = mapped_column(String(50), index=True)
    period_key: Mapped[str] = mapped_column(String(7))
    quantity: Mapped[int] = mapped_column(default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
