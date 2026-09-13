"""Meta channel configuration, OAuth onboarding, and signed webhook ingestion."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import (
    ChannelModel,
    ConversationModel,
    MessageModel,
    ProviderWebhookEventModel,
)
from app.domain.enums import (
    ChannelMode,
    ChannelType,
    MessageStatus,
    ProviderConnectionStatus,
)
from app.domain.errors import (
    AuthenticationError,
    ConflictError,
    ExternalProviderError,
    IntegrationNotConfiguredError,
    NotFoundError,
)
from app.domain.models import (
    MetaAccountOption,
    MetaChannelSettingsInput,
    MetaChannelStatus,
    MetaOAuthExchangeResult,
)
from app.repositories.provider_connection_repository import (
    OAuthTransactionRepository,
    ProviderConnectionRepository,
)
from app.services.conversations import ensure_channel, ingest_inbound_message
from app.services.credential_vault import decrypt_credentials

META_CHANNELS = {
    ChannelType.MESSENGER,
    ChannelType.INSTAGRAM_DM,
    ChannelType.FACEBOOK_COMMENTS,
    ChannelType.INSTAGRAM_COMMENTS,
}
REQUIRED_PERMISSIONS: dict[ChannelType, set[str]] = {
    ChannelType.MESSENGER: {
        "pages_messaging",
        "pages_manage_metadata",
        "pages_manage_posts",
    },
    ChannelType.FACEBOOK_COMMENTS: {
        "pages_read_engagement",
        "pages_manage_engagement",
        "pages_manage_posts",
    },
    ChannelType.INSTAGRAM_DM: {
        "instagram_basic",
        "instagram_content_publish",
        "instagram_manage_messages",
    },
    ChannelType.INSTAGRAM_COMMENTS: {
        "instagram_basic",
        "instagram_content_publish",
        "instagram_manage_comments",
    },
}
DEFAULT_OAUTH_PERMISSIONS = sorted(
    set().union(*REQUIRED_PERMISSIONS.values()) | {"pages_show_list", "business_management"}
)


def _mask(value: str) -> str | None:
    if not value:
        return None
    return f"{'*' * max(0, len(value) - 4)}{value[-4:]}"


def _ensure_meta_type(channel_type: ChannelType) -> None:
    if channel_type not in META_CHANNELS:
        raise ConflictError("Unsupported Meta channel type")


def _status(channel: ChannelModel, credentials: dict[str, str]) -> MetaChannelStatus:
    channel_type = ChannelType(channel.channel_type)
    permissions = list(channel.permissions_json or [])
    missing = sorted(REQUIRED_PERMISSIONS[channel_type] - set(permissions))
    expires_at = channel.token_expires_at
    expiring = False
    if expires_at is not None:
        aware = expires_at.replace(tzinfo=UTC) if expires_at.tzinfo is None else expires_at
        expiring = aware <= datetime.now(UTC) + timedelta(days=7)
    configured = channel.mode == ChannelMode.DEMO.value or (
        all(
            credentials.get(key)
            for key in ("account_id", "access_token", "app_secret", "verify_token")
        )
        and not missing
    )
    return MetaChannelStatus(
        channel_id=channel.id,
        channel_type=channel_type,
        mode=ChannelMode(channel.mode),
        display_name=channel.display_name,
        configured=configured,
        is_active=channel.is_active,
        masked_account_id=_mask(credentials.get("account_id", "")),
        permissions=permissions,
        missing_permissions=missing,
        token_expires_at=expires_at,
        token_expiring=expiring,
        webhook_path=f"/webhooks/meta/{channel.id}",
    )


def _credentials(
    session: Session,
    channel: ChannelModel,
    secret_key: str,
) -> dict[str, str]:
    if channel.provider_connection_id:
        return ProviderConnectionRepository(session, channel.store_id).credentials(
            channel.provider_connection_id
        )
    return decrypt_credentials(dict(channel.credentials_json), secret_key)


def list_meta_channels(session: Session, store_id: str, secret_key: str) -> list[MetaChannelStatus]:
    rows = session.scalars(
        select(ChannelModel).where(
            ChannelModel.store_id == store_id,
            ChannelModel.channel_type.in_([item.value for item in META_CHANNELS]),
        )
    ).all()
    return [_status(row, _credentials(session, row, secret_key)) for row in rows]


def save_meta_channel(
    session: Session,
    store_id: str,
    payload: MetaChannelSettingsInput,
    secret_key: str,
    *,
    health_verified: bool = False,
) -> MetaChannelStatus:
    _ensure_meta_type(payload.channel_type)
    channel = ensure_channel(
        session,
        store_id,
        payload.channel_type,
        mode=payload.mode,
        display_name=payload.display_name,
    )
    existing = _credentials(session, channel, secret_key)
    updates = {
        "account_id": payload.account_id,
        "access_token": payload.access_token,
        "app_secret": payload.app_secret,
        "verify_token": payload.verify_token,
    }
    credentials = {**existing, **{key: value for key, value in updates.items() if value}}
    if payload.mode == ChannelMode.LIVE:
        missing = [key for key in updates if not credentials.get(key)]
        if missing:
            raise ConflictError(
                "Meta live mode requires complete credentials",
                details={"missing": missing},
            )
    channel.mode = payload.mode.value
    channel.display_name = payload.display_name
    connection_type = (
        "instagram_business"
        if payload.channel_type in {ChannelType.INSTAGRAM_DM, ChannelType.INSTAGRAM_COMMENTS}
        else "facebook_page"
    )
    connection_channels = (
        {ChannelType.INSTAGRAM_DM, ChannelType.INSTAGRAM_COMMENTS}
        if connection_type == "instagram_business"
        else {ChannelType.MESSENGER, ChannelType.FACEBOOK_COMMENTS}
    )
    required_scopes = sorted(
        set().union(*(REQUIRED_PERMISSIONS[item] for item in connection_channels))
    )
    missing_permissions = set(required_scopes) - set(payload.permissions)
    initial_status = (
        ProviderConnectionStatus.CONNECTED
        if payload.mode == ChannelMode.DEMO or (health_verified and not missing_permissions)
        else ProviderConnectionStatus.PENDING
    )
    connection = ProviderConnectionRepository(session, store_id).upsert(
        provider="meta",
        connection_type=connection_type,
        external_resource_id=payload.account_id,
        external_account_id=payload.account_id,
        display_name=payload.display_name,
        credentials=credentials,
        scopes=payload.permissions,
        token_expires_at=payload.token_expires_at,
        metadata={"mode": payload.mode.value, "required_scopes": required_scopes},
        status=initial_status,
    )
    if payload.mode == ChannelMode.LIVE and missing_permissions:
        connection.status = ProviderConnectionStatus.ACTION_REQUIRED.value
        connection.last_error_code = "missing_permissions"
        connection.last_error_message = "Meta permissions are incomplete"
    channel.provider_connection_id = connection.id
    channel.credentials_json = {}
    channel.permissions_json = payload.permissions
    channel.token_expires_at = payload.token_expires_at
    channel.is_active = payload.is_active
    session.flush()
    return _status(channel, credentials)


def webhook_credentials(
    session: Session, channel_id: int, secret_key: str
) -> tuple[ChannelModel, dict[str, str]]:
    channel = session.scalar(
        select(ChannelModel).where(
            ChannelModel.id == channel_id,
            ChannelModel.channel_type.in_([item.value for item in META_CHANNELS]),
            ChannelModel.is_active.is_(True),
        )
    )
    if channel is None:
        raise NotFoundError(details={"entity": "meta_channel"})
    return channel, _credentials(session, channel, secret_key)


def verify_meta_signature(raw_body: bytes, signature: str | None, app_secret: str) -> None:
    if not signature or not signature.startswith("sha256=") or not app_secret:
        raise AuthenticationError("Invalid Meta webhook signature")
    expected = "sha256=" + hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise AuthenticationError("Invalid Meta webhook signature")


def _claim_event(
    session: Session,
    channel: ChannelModel,
    account_id: str,
    event_id: str,
    event_type: str,
) -> bool:
    try:
        with session.begin_nested():
            session.add(
                ProviderWebhookEventModel(
                    store_id=channel.store_id,
                    provider="meta",
                    external_account_id=account_id,
                    external_event_id=event_id,
                    event_type=event_type,
                )
            )
            session.flush()
        return True
    except IntegrityError:
        return False


def _update_meta_delivery(
    session: Session,
    store_id: str,
    message_ids: list[str],
) -> None:
    rows = session.scalars(
        select(MessageModel)
        .join(ConversationModel, ConversationModel.id == MessageModel.conversation_id)
        .where(
            ConversationModel.store_id == store_id,
            MessageModel.external_id.in_(message_ids),
        )
    ).all()
    for row in rows:
        if row.status in {MessageStatus.SENT.value, MessageStatus.QUEUED.value}:
            row.status = MessageStatus.DELIVERED.value


def process_meta_webhook(session: Session, channel: ChannelModel, payload: dict[str, Any]) -> int:
    channel_type = ChannelType(channel.channel_type)
    processed = 0
    for entry in payload.get("entry", []):
        account_id = str(entry.get("id", "")) or str(channel.id)
        for event in entry.get("messaging", []):
            delivery = event.get("delivery", {})
            mids = [str(value) for value in delivery.get("mids", []) if value]
            if mids:
                event_id = "delivery:" + ":".join(sorted(mids))
                if _claim_event(session, channel, account_id, event_id, "delivery"):
                    _update_meta_delivery(session, channel.store_id, mids)
                    processed += 1
                continue
            message = event.get("message", {})
            sender = str(event.get("sender", {}).get("id", ""))
            message_id = str(message.get("mid", ""))
            body = str(message.get("text", "")).strip()
            attachments = message.get("attachments", [])
            if not body and attachments:
                body = f"[{attachments[0].get('type', 'attachment')}]"
            if (
                not sender
                or not body
                or not message_id
                or not _claim_event(session, channel, account_id, message_id, "inbound_message")
            ):
                continue
            ingest_inbound_message(
                session,
                store_id=channel.store_id,
                channel_type=channel_type,
                external_user_id=sender,
                text=body,
                external_message_id=message_id,
                metadata={"meta_event": "message"},
            )
            processed += 1
        for change in entry.get("changes", []):
            value = change.get("value", {})
            if str(change.get("field", "")) not in {"feed", "comments", "mentions"}:
                continue
            sender = str(
                value.get("from", {}).get("id")
                or value.get("user_id")
                or value.get("sender_id")
                or ""
            )
            comment_id = str(
                value.get("comment_id") or value.get("id") or value.get("media_id") or ""
            )
            body = str(value.get("message") or value.get("text") or "").strip()
            if (
                not sender
                or not body
                or not comment_id
                or not _claim_event(session, channel, account_id, comment_id, "comment")
            ):
                continue
            ingest_inbound_message(
                session,
                store_id=channel.store_id,
                channel_type=channel_type,
                external_user_id=sender,
                text=body,
                display_name=str(value.get("from", {}).get("name", "")),
                external_message_id=comment_id or None,
                metadata={
                    "meta_event": "comment",
                    "author_id": sender,
                    "reply_target_id": comment_id,
                    "post_id": str(value.get("post_id") or value.get("media_id") or ""),
                },
            )
            processed += 1
    return processed


def verify_oauth_state(
    session: Session,
    state: str,
    user_id: str,
    store_id: str,
) -> None:
    OAuthTransactionRepository(session).validate(
        state=state,
        provider="meta",
        user_id=user_id,
        store_id=store_id,
    )


def oauth_start(
    session: Session,
    settings: Settings,
    user_id: str,
    store_id: str,
) -> tuple[str, str, bool]:
    _, state = OAuthTransactionRepository(session).create(
        provider="meta",
        user_id=user_id,
        store_id=store_id,
    )
    if not settings.meta_app_id or not settings.meta_app_secret.get_secret_value():
        if not settings.demo_mode:
            raise IntegrationNotConfiguredError("Meta OAuth is not configured")
        return (
            f"{settings.public_base_url}/meta/oauth/callback?code=demo&state={state}",
            state,
            True,
        )
    query = urlencode(
        {
            "client_id": settings.meta_app_id,
            "redirect_uri": settings.meta_oauth_redirect_uri,
            "state": state,
            "scope": ",".join(DEFAULT_OAUTH_PERMISSIONS),
            "response_type": "code",
        }
    )
    return (
        f"https://www.facebook.com/{settings.meta_graph_api_version}/dialog/oauth?{query}",
        state,
        False,
    )


def exchange_oauth_code(
    session: Session,
    settings: Settings,
    code: str,
    state: str,
    user_id: str,
    store_id: str,
) -> MetaOAuthExchangeResult:
    oauth_transactions = OAuthTransactionRepository(session)
    transaction = oauth_transactions.consume(
        state=state,
        provider="meta",
        user_id=user_id,
        store_id=store_id,
    )
    if code == "demo":
        if not settings.demo_mode:
            raise AuthenticationError("Demo Meta OAuth is disabled")
        accounts = [
            MetaAccountOption(
                page_id="demo-page",
                page_name="Demo Facebook Page",
                instagram_account_id="demo-instagram",
                instagram_username="demo.store",
            )
        ]
        token_data = {
            "access_token": "demo-token",
            "mode": "demo",
            "permissions": json.dumps(DEFAULT_OAUTH_PERMISSIONS),
        }
    else:
        if not settings.meta_app_id or not settings.meta_app_secret.get_secret_value():
            raise ConflictError("Meta OAuth is not configured")
        base = f"{settings.meta_graph_api_base.rstrip('/')}/{settings.meta_graph_api_version}"
        try:
            token_response = httpx.get(
                f"{base}/oauth/access_token",
                params={
                    "client_id": settings.meta_app_id,
                    "client_secret": settings.meta_app_secret.get_secret_value(),
                    "redirect_uri": settings.meta_oauth_redirect_uri,
                    "code": code,
                },
                timeout=settings.meta_request_timeout_seconds,
            )
            token_response.raise_for_status()
            short_token = str(token_response.json()["access_token"])
            long_lived_response = httpx.get(
                f"{base}/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": settings.meta_app_id,
                    "client_secret": settings.meta_app_secret.get_secret_value(),
                    "fb_exchange_token": short_token,
                },
                timeout=settings.meta_request_timeout_seconds,
            )
            long_lived_response.raise_for_status()
            user_token = str(long_lived_response.json()["access_token"])
            permissions_response = httpx.get(
                f"{base}/me/permissions",
                params={"access_token": user_token},
                timeout=settings.meta_request_timeout_seconds,
            )
            permissions_response.raise_for_status()
            pages_response = httpx.get(
                f"{base}/me/accounts",
                params={
                    "fields": "id,name,access_token,instagram_business_account{id,username}",
                    "access_token": user_token,
                },
                timeout=settings.meta_request_timeout_seconds,
            )
            pages_response.raise_for_status()
        except (httpx.HTTPError, KeyError) as exc:
            raise ExternalProviderError("Meta OAuth exchange failed") from exc
        page_rows = pages_response.json().get("data", [])
        granted_permissions = sorted(
            str(item.get("permission"))
            for item in permissions_response.json().get("data", [])
            if item.get("status") == "granted" and item.get("permission")
        )
        accounts = [
            MetaAccountOption(
                page_id=str(row["id"]),
                page_name=str(row.get("name", row["id"])),
                instagram_account_id=(
                    str(row["instagram_business_account"]["id"])
                    if row.get("instagram_business_account")
                    else None
                ),
                instagram_username=(
                    str(row["instagram_business_account"].get("username", ""))
                    if row.get("instagram_business_account")
                    else None
                ),
            )
            for row in page_rows
        ]
        token_data = {
            "access_token": user_token,
            "page_tokens": json.dumps(
                {str(row["id"]): str(row["access_token"]) for row in page_rows}
            ),
            "mode": "live",
            "permissions": json.dumps(granted_permissions),
        }
    oauth_transactions.store_exchange_result(
        transaction,
        credentials=token_data,
        metadata={"accounts": [item.model_dump(mode="json") for item in accounts]},
    )
    return MetaOAuthExchangeResult(
        transaction_id=transaction.id,
        accounts=accounts,
    )


def connect_oauth_account(
    session: Session,
    settings: Settings,
    store_id: str,
    user_id: str,
    transaction_id: str,
    page_id: str,
    instagram_account_id: str | None,
) -> list[MetaChannelStatus]:
    oauth_transactions = OAuthTransactionRepository(session)
    transaction, token_data = oauth_transactions.pending_result(
        transaction_id=transaction_id,
        provider="meta",
        user_id=user_id,
        store_id=store_id,
    )
    account_payload = transaction.result_metadata_json.get("accounts", [])
    accounts = [MetaAccountOption.model_validate(item) for item in account_payload]
    selected = next((item for item in accounts if item.page_id == page_id), None)
    if selected is None:
        raise ConflictError("Selected Meta Page is not part of this OAuth session")
    mode = ChannelMode(token_data.get("mode", "demo"))
    page_tokens = json.loads(token_data.get("page_tokens", "{}"))
    access_token = str(page_tokens.get(page_id) or token_data["access_token"])
    granted_permissions = set(json.loads(token_data.get("permissions", "[]")))
    verify_token = hashlib.sha256(
        f"{store_id}:{page_id}:{settings.effective_secret_key}".encode()
    ).hexdigest()[:32]
    app_secret = settings.meta_app_secret.get_secret_value()
    if not app_secret and settings.demo_mode:
        app_secret = "demo-meta-app-secret"
    if not app_secret:
        raise IntegrationNotConfiguredError("Meta App Secret is not configured")
    if mode == ChannelMode.LIVE:
        base = f"{settings.meta_graph_api_base.rstrip('/')}/{settings.meta_graph_api_version}"
        try:
            page_subscription = httpx.post(
                f"{base}/{page_id}/subscribed_apps",
                data={
                    "subscribed_fields": "messages,messaging_postbacks,feed",
                    "access_token": access_token,
                },
                timeout=settings.meta_request_timeout_seconds,
            )
            page_subscription.raise_for_status()
            if instagram_account_id:
                instagram_subscription = httpx.post(
                    f"{base}/{instagram_account_id}/subscribed_apps",
                    data={
                        "subscribed_fields": "messages,comments,mentions",
                        "access_token": access_token,
                    },
                    timeout=settings.meta_request_timeout_seconds,
                )
                instagram_subscription.raise_for_status()
        except httpx.HTTPError as exc:
            raise ExternalProviderError("Meta webhook subscription failed") from exc
    statuses: list[MetaChannelStatus] = []
    for channel_type, account_id, name in (
        (ChannelType.MESSENGER, page_id, f"{selected.page_name} Messenger"),
        (ChannelType.FACEBOOK_COMMENTS, page_id, f"{selected.page_name} Comments"),
        (
            ChannelType.INSTAGRAM_DM,
            instagram_account_id or "",
            "Instagram Direct",
        ),
        (
            ChannelType.INSTAGRAM_COMMENTS,
            instagram_account_id or "",
            "Instagram Comments",
        ),
    ):
        if not account_id:
            continue
        statuses.append(
            save_meta_channel(
                session,
                store_id,
                MetaChannelSettingsInput(
                    channel_type=channel_type,
                    mode=mode,
                    display_name=name,
                    account_id=account_id,
                    access_token=access_token,
                    app_secret=app_secret,
                    verify_token=verify_token,
                    permissions=sorted(granted_permissions),
                ),
                settings.effective_secret_key,
                health_verified=mode == ChannelMode.LIVE,
            )
        )
    oauth_transactions.complete(transaction)
    return statuses
