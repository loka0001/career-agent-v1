"""Generated public slice of models.py."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.domain.enums import ChannelType, ConversationPriority, ConversationStatus, EventType
from app.domain.model_groups.sales import Recommendation
from app.domain.model_groups.shared import ContractModel, MoneyModel


class NoteInput(ContractModel):
    text: str = Field(min_length=1, max_length=4000)


class ConversationUpdateInput(ContractModel):
    status: ConversationStatus | None = None
    priority: ConversationPriority | None = None
    assignee_user_id: str | None = None
    tags: list[str] | None = Field(default=None, max_length=20)


class SimulateInboundInput(ContractModel):
    """Demo-mode helper: inject a realistic inbound customer message."""

    text: str = Field(min_length=1, max_length=2000)
    customer_name: str = Field(default="عميل تجريبي", max_length=160)
    external_id: str | None = Field(default=None, max_length=160)
    channel_type: ChannelType = ChannelType.WEBCHAT


class ApiKeySummary(ContractModel):
    id: int
    name: str
    key_prefix: str
    key_type: str
    scopes: list[str]
    allowed_origins: list[str]
    is_active: bool
    created_at: datetime
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None


class ApiKeyCreateInput(ContractModel):
    name: str = Field(min_length=1, max_length=120)
    allowed_origins: list[str] = Field(min_length=1, max_length=20)


class ApiKeyCreatedResponse(ContractModel):
    key: str
    api_key: ApiKeySummary


class PublicChatInput(ContractModel):
    session_key: str = Field(min_length=8, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    message: str = Field(min_length=1, max_length=2000)
    customer_name: str = Field(default="زائر الموقع", max_length=160)
    page_url: str = Field(default="", max_length=500)


class PublicChatResponse(ContractModel):
    conversation_id: int
    reply: str
    recommendations: list[Recommendation] = Field(max_length=3)
    citations: list[str] = Field(default_factory=list)
    insufficient_context: bool = False


class TrackEventInput(ContractModel):
    session_key: str = Field(min_length=8, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    event_type: EventType
    product_id: str | None = Field(default=None, max_length=64)
    payload: dict[str, str | int | float | bool] = Field(default_factory=dict)
    consented: bool = False


class TrackEventsBatchInput(ContractModel):
    events: list[TrackEventInput] = Field(min_length=1, max_length=20)


class PublicCatalogItem(MoneyModel):
    product_id: str
    name: str
    category: str
    price: Decimal
    stock: int
    description: str
    image_url: str | None = None
