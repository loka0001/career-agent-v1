"""Generated customers slice of models.py."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.model_groups.shared import utc_now


class CustomerModel(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    display_name: Mapped[str] = mapped_column(String(160), default="")
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    tags_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    consent_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    attributes_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    lead_score: Mapped[int] = mapped_column(default=0)
    merged_into_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id"), nullable=True, index=True
    )
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class CustomerConsentModel(Base):
    __tablename__ = "customer_consents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    channel_type: Mapped[str] = mapped_column(String(30), index=True)
    status: Mapped[str] = mapped_column(String(20), index=True)
    source: Mapped[str] = mapped_column(String(60))
    consent_text: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ProviderWebhookEventModel(Base):
    __tablename__ = "provider_webhook_events"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "external_account_id",
            "external_event_id",
            name="uq_provider_webhook_event",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    external_account_id: Mapped[str] = mapped_column(String(255), index=True)
    external_event_id: Mapped[str] = mapped_column(String(255))
    event_type: Mapped[str] = mapped_column(String(80))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class CustomerIdentityModel(Base):
    __tablename__ = "customer_identities"
    __table_args__ = (
        UniqueConstraint(
            "store_id", "channel_type", "external_id", name="uq_identity_store_channel_ext"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    channel_type: Mapped[str] = mapped_column(String(30))
    external_id: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ConversationModel(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    priority: Mapped[str] = mapped_column(String(10), default="normal", index=True)
    assignee_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    last_message_preview: Mapped[str] = mapped_column(String(300), default="")
    unread_count: Mapped[int] = mapped_column(default=0)
    tags_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    last_inbound_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_outbound_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sla_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, index=True
    )

    messages: Mapped[list[MessageModel]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class MessageModel(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index(
            "uq_message_conversation_external",
            "conversation_id",
            "external_id",
            unique=True,
        ),
        Index(
            "uq_message_conversation_client_request",
            "conversation_id",
            "client_request_id",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    direction: Mapped[str] = mapped_column(String(10))
    sender_type: Mapped[str] = mapped_column(String(15))
    sender_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    body: Mapped[str] = mapped_column(Text)
    attachments_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(15), default="received", index=True)
    external_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    client_request_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )

    conversation: Mapped[ConversationModel] = relationship(back_populates="messages")
