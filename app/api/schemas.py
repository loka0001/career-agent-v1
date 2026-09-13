"""API-only request and response contracts."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import Platform
from app.domain.models import (
    AuthUser,
    ConversationSummary,
    IntegrationStatus,
    PublishResult,
    StoreSummary,
)


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginResponse(ApiModel):
    user: AuthUser
    csrf_token: str
    is_operator: bool = False
    demo_mode: bool = False


class RegistrationResponse(ApiModel):
    verification_required: bool
    email: str
    user: AuthUser | None = None
    csrf_token: str | None = None


class StoreListResponse(ApiModel):
    stores: list[StoreSummary]


class ConversationListResponse(ApiModel):
    conversations: list[ConversationSummary]
    demo_available: bool = False


class MessageResponse(ApiModel):
    message: str


class PublishRequest(ApiModel):
    platforms: list[Platform] = Field(
        min_length=1,
        max_length=2,
        examples=[[Platform.FACEBOOK, Platform.INSTAGRAM]],
    )


class PublishResponse(ApiModel):
    results: list[PublishResult]


class IntegrationStatusResponse(ApiModel):
    integrations: list[IntegrationStatus]


class ReadyResponse(ApiModel):
    status: str
    checks: dict[str, bool]


class ErrorBody(ApiModel):
    code: str
    message: str
    details: dict[str, Any]
    request_id: str


class ErrorEnvelope(ApiModel):
    error: ErrorBody
