"""Generated messaging slice of models.py."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.domain.enums import (
    ChannelMode,
    ChannelType,
    ConversationPriority,
    ConversationStatus,
    MessageDirection,
    MessageSenderType,
    MessageStatus,
)
from app.domain.model_groups.sales import CustomerSummary
from app.domain.model_groups.shared import ContractModel


class MessageOut(ContractModel):
    id: int
    direction: MessageDirection
    sender_type: MessageSenderType
    body: str
    attachments: list[dict[str, Any]] = Field(
        default_factory=list,
        validation_alias="attachments_json",
    )
    status: MessageStatus
    external_id: str | None = None
    error_message: str | None = None
    created_at: datetime


class ConversationSummary(ContractModel):
    id: int
    channel_type: ChannelType
    status: ConversationStatus
    priority: ConversationPriority
    customer: CustomerSummary
    assignee_user_id: str | None = None
    last_message_preview: str
    unread_count: int
    tags: list[str] = Field(default_factory=list)
    sla_overdue: bool = False
    last_inbound_at: datetime | None = None
    last_outbound_at: datetime | None = None
    updated_at: datetime


class ConversationDetail(ConversationSummary):
    messages: list[MessageOut] = Field(default_factory=list)


class ReplyInput(ContractModel):
    text: str = Field(min_length=1, max_length=4000)


class TemplateReplyInput(ContractModel):
    template_id: int = Field(gt=0)
    variables: dict[str, str] = Field(default_factory=dict, max_length=20)


class WhatsAppSettingsInput(ContractModel):
    mode: ChannelMode = ChannelMode.DEMO
    display_name: str = Field(default="WhatsApp Business", min_length=1, max_length=160)
    phone_number_id: str = Field(default="", max_length=80)
    waba_id: str = Field(default="", max_length=80)
    access_token: str = Field(default="", max_length=4096)
    app_secret: str = Field(default="", max_length=512)
    verify_token: str = Field(default="", max_length=512)
    is_active: bool = True


class WhatsAppSettingsStatus(ContractModel):
    channel_id: int | None
    mode: ChannelMode
    demo_available: bool
    display_name: str
    configured: bool
    is_active: bool
    masked_phone_number_id: str | None = None
    masked_waba_id: str | None = None
    webhook_path: str
    embedded_signup_available: bool = False
    connection_status: str = "disconnected"


class WhatsAppConnectionCheck(ContractModel):
    success: bool
    error_code: str | None = None


class WhatsAppTemplateInput(ContractModel):
    name: str = Field(min_length=1, max_length=160, pattern=r"^[a-z0-9_]+$")
    language: str = Field(default="ar", min_length=2, max_length=16)
    body: str = Field(min_length=1, max_length=4000)
    variables: list[str] = Field(default_factory=list, max_length=20)
    category: str = Field(
        default="UTILITY",
        pattern=r"^(UTILITY|MARKETING|AUTHENTICATION)$",
    )


class WhatsAppTemplateOut(ContractModel):
    id: int
    name: str
    language: str
    body: str
    variables: list[str] = Field(default_factory=list)
    external_id: str | None = None
    category: str = "UTILITY"
    status: str
    rejection_reason: str | None = None
    quality_score: str | None = None
    last_synced_at: datetime | None = None
    created_at: datetime


class WhatsAppEmbeddedStartOut(ContractModel):
    app_id: str
    config_id: str
    api_version: str
    state: str
    solution_id: str | None = None


class WhatsAppEmbeddedExchangeInput(ContractModel):
    code: str = Field(min_length=4, max_length=4096)
    state: str = Field(min_length=20, max_length=512)
    waba_id: str | None = Field(default=None, max_length=80)


class WhatsAppPhoneOption(ContractModel):
    phone_number_id: str
    waba_id: str
    display_phone_number: str
    verified_name: str
    quality_rating: str
    verification_status: str


class WhatsAppEmbeddedExchangeOut(ContractModel):
    transaction_id: str
    phones: list[WhatsAppPhoneOption]


class WhatsAppEmbeddedConnectInput(ContractModel):
    transaction_id: str = Field(min_length=10, max_length=100)
    phone_number_id: str = Field(min_length=1, max_length=80)
    waba_id: str = Field(min_length=1, max_length=80)
    registration_pin: str | None = Field(default=None, pattern=r"^\d{6}$")
