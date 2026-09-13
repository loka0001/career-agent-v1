"""Generated integrations slice of models.py."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.model_groups.shared import utc_now


class ProviderConnectionModel(Base):
    __tablename__ = "provider_connections"
    __table_args__ = (
        UniqueConstraint(
            "store_id",
            "provider",
            "connection_type",
            "external_resource_id",
            name="uq_provider_connection_resource",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    connection_type: Mapped[str] = mapped_column(String(60), index=True)
    external_account_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_business_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_resource_id: Mapped[str] = mapped_column(String(255), default="")
    display_name: Mapped[str] = mapped_column(String(160), default="")
    credentials_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    scopes_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    capabilities_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_health_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_successful_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class OAuthTransactionModel(Base):
    __tablename__ = "oauth_transactions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    state_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    nonce_hash: Mapped[str] = mapped_column(String(64), unique=True)
    result_credentials_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result_metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ChannelModel(Base):
    __tablename__ = "channels"
    __table_args__ = (UniqueConstraint("store_id", "channel_type", name="uq_channel_store_type"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    provider_connection_id: Mapped[str | None] = mapped_column(
        ForeignKey("provider_connections.id"), nullable=True, index=True
    )
    channel_type: Mapped[str] = mapped_column(String(30), index=True)
    mode: Mapped[str] = mapped_column(String(10), default="demo")
    display_name: Mapped[str] = mapped_column(String(160), default="")
    credentials_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    permissions_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class ChannelTemplateModel(Base):
    __tablename__ = "channel_templates"
    __table_args__ = (
        UniqueConstraint(
            "store_id",
            "channel_id",
            "name",
            "language",
            name="uq_channel_template_name_language",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    language: Mapped[str] = mapped_column(String(16), default="ar")
    body: Mapped[str] = mapped_column(Text)
    variables_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    external_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    category: Mapped[str] = mapped_column(String(30), default="UTILITY")
    status: Mapped[str] = mapped_column(String(20), default="approved", index=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    quality_score: Mapped[str | None] = mapped_column(String(30), nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
