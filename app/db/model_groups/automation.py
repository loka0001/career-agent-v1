"""Generated automation slice of models.py."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.model_groups.shared import utc_now


class OpportunityModel(Base):
    __tablename__ = "opportunities"
    __table_args__ = (UniqueConstraint("store_id", "dedup_key", name="uq_opportunity_store_dedup"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id"), nullable=True, index=True
    )
    opportunity_type: Mapped[str] = mapped_column(String(60), index=True)
    dedup_key: Mapped[str] = mapped_column(String(180))
    related_product_ids_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    reason: Mapped[str] = mapped_column(Text)
    expected_revenue_numeric: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    realized_revenue_numeric: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    confidence: Mapped[int]
    suggested_action: Mapped[str] = mapped_column(Text)
    channel: Mapped[str | None] = mapped_column(String(30), nullable=True)
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="new", index=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    execute_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class OpportunityActionModel(Base):
    __tablename__ = "opportunity_actions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunities.id"), index=True)
    action: Mapped[str] = mapped_column(String(40))
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AutomationModel(Base):
    __tablename__ = "automations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    trigger_type: Mapped[str] = mapped_column(String(50), index=True)
    conditions_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    actions_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    delay_seconds: Mapped[int] = mapped_column(default=0)
    approval_required: Mapped[bool] = mapped_column(default=False)
    is_enabled: Mapped[bool] = mapped_column(default=True, index=True)
    template_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class AutomationRunModel(Base):
    __tablename__ = "automation_runs"
    __table_args__ = (
        UniqueConstraint("automation_id", "event_key", name="uq_automation_run_event"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    automation_id: Mapped[int] = mapped_column(ForeignKey("automations.id"), index=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    event_key: Mapped[str] = mapped_column(String(180))
    event_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class StoreBrandModel(Base):
    __tablename__ = "store_brands"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), unique=True, index=True)
    tone: Mapped[str] = mapped_column(String(80), default="friendly")
    audience: Mapped[str] = mapped_column(Text, default="")
    guidelines: Mapped[str] = mapped_column(Text, default="")
    primary_color: Mapped[str] = mapped_column(String(20), default="#6366f1")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class ContentCampaignModel(Base):
    __tablename__ = "content_campaigns"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    goal: Mapped[str] = mapped_column(String(160))
    budget_numeric: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    product_ids_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    concept: Mapped[str] = mapped_column(Text)
    audience: Mapped[str] = mapped_column(Text)
    offer: Mapped[str] = mapped_column(Text)
    landing_copy: Mapped[str] = mapped_column(Text)
    whatsapp_template: Mapped[str] = mapped_column(Text)
    kpis_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ContentItemModel(Base):
    __tablename__ = "content_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    campaign_id: Mapped[int | None] = mapped_column(
        ForeignKey("content_campaigns.id"), nullable=True, index=True
    )
    product_id: Mapped[str] = mapped_column(String(64))
    content_format: Mapped[str] = mapped_column(String(40))
    platform: Mapped[str] = mapped_column(String(20))
    tone: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text)
    caption: Mapped[str] = mapped_column(Text)
    hashtags_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    cta: Mapped[str] = mapped_column(String(300))
    validation_warnings_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    current_version: Mapped[int] = mapped_column(default=1)
    scheduled_for: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(320), nullable=True)
    approved_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    approved_content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class ContentVersionModel(Base):
    __tablename__ = "content_versions"
    __table_args__ = (
        UniqueConstraint("content_item_id", "version", name="uq_content_item_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    content_item_id: Mapped[int] = mapped_column(ForeignKey("content_items.id"), index=True)
    version: Mapped[int]
    snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
