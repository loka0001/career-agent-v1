"""Meta channel onboarding, encrypted settings, and signed webhooks."""

from __future__ import annotations

import hmac
import json
from typing import Annotated, Any
from urllib.parse import urlencode

from fastapi import APIRouter, Header, Query, Request, Response
from fastapi.responses import RedirectResponse

from app.api.dependencies import AdminUser, ContainerDependency, CurrentUser, DatabaseDependency
from app.api.request_body import read_bounded_body
from app.domain.enums import ChannelMode, ChannelType
from app.domain.errors import AuthenticationError, ConflictError, InvalidInputError
from app.domain.models import (
    MetaChannelSettingsInput,
    MetaChannelStatus,
    MetaOAuthConnectInput,
    MetaOAuthExchangeInput,
    MetaOAuthExchangeResult,
    MetaOAuthStart,
)
from app.integrations.channels import resolve_adapter
from app.services.meta_channels import (
    connect_oauth_account,
    exchange_oauth_code,
    list_meta_channels,
    oauth_start,
    process_meta_webhook,
    save_meta_channel,
    verify_meta_signature,
    verify_oauth_state,
    webhook_credentials,
)

router = APIRouter(prefix="/integrations/meta/channels", tags=["meta-channels"])
webhook_router = APIRouter(prefix="/webhooks/meta", tags=["meta-webhook"])
oauth_callback_router = APIRouter(prefix="/meta/oauth", tags=["meta-oauth"])


@router.get("", response_model=list[MetaChannelStatus])
def channels(
    user: CurrentUser, container: ContainerDependency, db: DatabaseDependency
) -> list[MetaChannelStatus]:
    return list_meta_channels(
        db, user.store_id, container.settings.effective_secret_key
    )


@router.put("/{channel_type}", response_model=MetaChannelStatus)
def update_channel(
    channel_type: str,
    payload: MetaChannelSettingsInput,
    user: AdminUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> MetaChannelStatus:
    if payload.channel_type.value != channel_type:
        raise InvalidInputError("Channel type path and payload do not match")
    if payload.mode == ChannelMode.DEMO and not container.settings.demo_mode:
        raise ConflictError("Demo channel mode is disabled")
    return save_meta_channel(
        db,
        user.store_id,
        payload,
        container.settings.effective_secret_key,
    )


@router.post("/{channel_id}/check")
def check_channel(
    channel_id: int,
    user: AdminUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> dict[str, str | bool | None]:
    row, credentials = webhook_credentials(
        db, channel_id, container.settings.effective_secret_key
    )
    if row.store_id != user.store_id:
        raise AuthenticationError("Meta channel is not available")
    adapter = resolve_adapter(
        ChannelType(row.channel_type), ChannelMode(row.mode)
    )
    success, error = adapter.check_connection(credentials)
    return {"success": success, "error_code": error}


@router.post("/oauth/start", response_model=MetaOAuthStart)
def start_oauth(
    user: AdminUser, container: ContainerDependency, db: DatabaseDependency
) -> MetaOAuthStart:
    url, state, demo = oauth_start(
        db, container.settings, user.user_id, user.store_id
    )
    return MetaOAuthStart(authorization_url=url, state=state, demo=demo)


@router.post("/oauth/exchange", response_model=MetaOAuthExchangeResult)
def exchange(
    payload: MetaOAuthExchangeInput,
    user: AdminUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> MetaOAuthExchangeResult:
    return exchange_oauth_code(
        db,
        container.settings,
        payload.code,
        payload.state,
        user.user_id,
        user.store_id,
    )


@router.post("/oauth/connect", response_model=list[MetaChannelStatus])
def connect(
    payload: MetaOAuthConnectInput,
    user: AdminUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> list[MetaChannelStatus]:
    return connect_oauth_account(
        db,
        container.settings,
        user.store_id,
        user.user_id,
        payload.transaction_id,
        payload.page_id,
        payload.instagram_account_id,
    )


@oauth_callback_router.get("/callback")
def oauth_callback(
    code: str,
    state: str,
    user: CurrentUser,
    db: DatabaseDependency,
) -> RedirectResponse:
    verify_oauth_state(
        db,
        state,
        user.user_id,
        user.store_id,
    )
    query = urlencode({"meta_code": code, "meta_state": state})
    return RedirectResponse(f"/app/integrations?{query}")


@webhook_router.get("/{channel_id}")
def verify_webhook(
    channel_id: int,
    container: ContainerDependency,
    db: DatabaseDependency,
    mode: Annotated[str | None, Query(alias="hub.mode")] = None,
    verify_token: Annotated[str | None, Query(alias="hub.verify_token")] = None,
    challenge: Annotated[str | None, Query(alias="hub.challenge")] = None,
) -> Response:
    _, credentials = webhook_credentials(
        db, channel_id, container.settings.effective_secret_key
    )
    expected = credentials.get("verify_token", "")
    if (
        mode != "subscribe"
        or not verify_token
        or not expected
        or not hmac.compare_digest(verify_token, expected)
    ):
        raise AuthenticationError("Invalid Meta webhook verification token")
    return Response(challenge or "", media_type="text/plain")


@webhook_router.post("/{channel_id}")
async def receive_webhook(
    channel_id: int,
    request: Request,
    container: ContainerDependency,
    db: DatabaseDependency,
    signature: Annotated[str | None, Header(alias="X-Hub-Signature-256")] = None,
) -> dict[str, Any]:
    raw = await read_bounded_body(request, max_bytes=2 * 1024 * 1024, label="Meta webhook")
    channel, credentials = webhook_credentials(
        db, channel_id, container.settings.effective_secret_key
    )
    verify_meta_signature(raw, signature, credentials.get("app_secret", ""))
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InvalidInputError("Invalid Meta webhook JSON") from exc
    if not isinstance(payload, dict):
        raise InvalidInputError("Invalid Meta webhook payload")
    return {"received": True, "processed": process_meta_webhook(db, channel, payload)}
