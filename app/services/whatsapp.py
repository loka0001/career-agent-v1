"""WhatsApp settings, templates, signed webhook parsing, and message statuses."""

from __future__ import annotations

import hashlib
import hmac
import re
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import (
    ChannelModel,
    ChannelTemplateModel,
    ConversationModel,
    CustomerConsentModel,
    CustomerModel,
    MessageModel,
    ProviderWebhookEventModel,
)
from app.domain.enums import (
    ChannelMode,
    ChannelType,
    MessageStatus,
    ProviderConnectionStatus,
)
from app.domain.errors import AuthorizationError, ConflictError, NotFoundError
from app.domain.models import (
    WhatsAppSettingsInput,
    WhatsAppSettingsStatus,
    WhatsAppTemplateInput,
    WhatsAppTemplateOut,
)
from app.integrations.channels import resolve_adapter
from app.integrations.whatsapp import WhatsAppManagementClient
from app.repositories.provider_connection_repository import ProviderConnectionRepository
from app.services.conversations import ensure_channel, ingest_inbound_message
from app.services.credential_vault import decrypt_credentials

OPT_OUT_WORDS = {"stop", "unsubscribe", "cancel", "الغاء", "إلغاء", "توقف"}
OPT_IN_WORDS = {"start", "subscribe", "yes", "ابدأ", "موافق"}
STATUS_ORDER = {
    MessageStatus.QUEUED.value: 0,
    MessageStatus.SENT.value: 1,
    MessageStatus.DELIVERED.value: 2,
    MessageStatus.READ.value: 3,
    MessageStatus.FAILED.value: 4,
}


def _mask(value: str) -> str | None:
    if not value:
        return None
    if len(value) <= 4:
        return "*" * len(value)
    return f"{'*' * (len(value) - 4)}{value[-4:]}"


def _status(
    channel: ChannelModel,
    credentials: dict[str, str],
    *,
    demo_available: bool = True,
    embedded_signup_available: bool = False,
    connection_status: str = "disconnected",
) -> WhatsAppSettingsStatus:
    required = ("phone_number_id", "waba_id", "access_token", "app_secret", "verify_token")
    configured = channel.mode == ChannelMode.DEMO.value or all(
        credentials.get(name) for name in required
    )
    return WhatsAppSettingsStatus(
        channel_id=channel.id,
        mode=ChannelMode(channel.mode),
        demo_available=demo_available,
        display_name=channel.display_name,
        configured=configured,
        is_active=channel.is_active,
        masked_phone_number_id=_mask(credentials.get("phone_number_id", "")),
        masked_waba_id=_mask(credentials.get("waba_id", "")),
        webhook_path=f"/webhooks/whatsapp/{channel.id}",
        embedded_signup_available=embedded_signup_available,
        connection_status=connection_status,
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


def get_settings_status(
    session: Session,
    store_id: str,
    secret_key: str,
    *,
    demo_available: bool = True,
    embedded_signup_available: bool = False,
) -> WhatsAppSettingsStatus:
    channel = session.scalar(
        select(ChannelModel).where(
            ChannelModel.store_id == store_id,
            ChannelModel.channel_type == ChannelType.WHATSAPP.value,
        )
    )
    if channel is None:
        return WhatsAppSettingsStatus(
            channel_id=None,
            mode=ChannelMode.DEMO if demo_available else ChannelMode.LIVE,
            demo_available=demo_available,
            display_name="WhatsApp Business",
            configured=False,
            is_active=False,
            masked_phone_number_id=None,
            masked_waba_id=None,
            webhook_path="",
            embedded_signup_available=embedded_signup_available,
            connection_status="disconnected",
        )
    credentials = _credentials(session, channel, secret_key)
    connection_status = "disconnected"
    if channel.provider_connection_id:
        connection_status = (
            ProviderConnectionRepository(session, store_id)
            .get(channel.provider_connection_id)
            .status
        )
    return _status(
        channel,
        credentials,
        demo_available=demo_available,
        embedded_signup_available=embedded_signup_available,
        connection_status=connection_status,
    )


def save_settings(
    session: Session,
    store_id: str,
    payload: WhatsAppSettingsInput,
    secret_key: str,
    *,
    demo_available: bool = True,
) -> WhatsAppSettingsStatus:
    channel = ensure_channel(
        session,
        store_id,
        ChannelType.WHATSAPP,
        mode=payload.mode,
        display_name=payload.display_name,
    )
    existing = _credentials(session, channel, secret_key)
    updates = {
        "phone_number_id": payload.phone_number_id,
        "waba_id": payload.waba_id,
        "access_token": payload.access_token,
        "app_secret": payload.app_secret,
        "verify_token": payload.verify_token,
    }
    credentials = {**existing, **{key: value for key, value in updates.items() if value}}
    if payload.mode == ChannelMode.LIVE:
        missing = [key for key, value in updates.items() if not credentials.get(key)]
        if missing:
            raise ConflictError(
                "WhatsApp live mode requires complete credentials",
                details={"missing": missing},
            )
    channel.mode = payload.mode.value
    channel.display_name = payload.display_name
    channel.is_active = payload.is_active
    connection = ProviderConnectionRepository(session, store_id).upsert(
        provider="meta",
        connection_type="whatsapp_business",
        external_resource_id=credentials.get("phone_number_id", ""),
        external_account_id=credentials.get("phone_number_id") or None,
        external_business_id=credentials.get("waba_id") or None,
        display_name=payload.display_name,
        credentials=credentials,
        scopes=["whatsapp_business_messaging", "whatsapp_business_management"],
        metadata={"mode": payload.mode.value},
        status=ProviderConnectionStatus.PENDING,
    )
    channel.provider_connection_id = connection.id
    channel.credentials_json = {}
    refresh_connection_health(session, channel, credentials)
    return _status(
        channel,
        credentials,
        demo_available=demo_available,
        connection_status=connection.status,
    )


def refresh_connection_health(
    session: Session,
    channel: ChannelModel,
    credentials: dict[str, str],
) -> tuple[bool, str | None]:
    if not channel.provider_connection_id:
        return False, "not_configured"
    connection = ProviderConnectionRepository(session, channel.store_id).get(
        channel.provider_connection_id
    )
    adapter = resolve_adapter(ChannelType.WHATSAPP, ChannelMode(channel.mode))
    healthy, error_code = adapter.check_connection(credentials)
    connection.status = (
        ProviderConnectionStatus.CONNECTED.value
        if healthy
        else ProviderConnectionStatus.DEGRADED.value
    )
    connection.last_health_at = datetime.now(UTC)
    connection.last_error_code = error_code
    connection.last_error_message = None if healthy else "WhatsApp connection health check failed"
    session.flush()
    return healthy, error_code


def _template_out(row: ChannelTemplateModel) -> WhatsAppTemplateOut:
    return WhatsAppTemplateOut(
        id=row.id,
        name=row.name,
        language=row.language,
        body=row.body,
        variables=list(row.variables_json),
        external_id=row.external_id,
        category=row.category,
        status=row.status,
        rejection_reason=row.rejection_reason,
        quality_score=row.quality_score,
        last_synced_at=row.last_synced_at,
        created_at=row.created_at,
    )


def list_templates(session: Session, store_id: str, channel_id: int) -> list[WhatsAppTemplateOut]:
    rows = session.scalars(
        select(ChannelTemplateModel)
        .where(
            ChannelTemplateModel.store_id == store_id,
            ChannelTemplateModel.channel_id == channel_id,
        )
        .order_by(ChannelTemplateModel.created_at.desc())
    ).all()
    return [_template_out(row) for row in rows]


def create_template(
    session: Session,
    store_id: str,
    channel_id: int,
    payload: WhatsAppTemplateInput,
    client: WhatsAppManagementClient | None = None,
    secret_key: str = "",
) -> WhatsAppTemplateOut:
    channel = session.scalar(
        select(ChannelModel).where(
            ChannelModel.id == channel_id,
            ChannelModel.store_id == store_id,
            ChannelModel.channel_type == ChannelType.WHATSAPP.value,
        )
    )
    if channel is None:
        raise NotFoundError(details={"entity": "channel", "id": channel_id})
    existing = session.scalar(
        select(ChannelTemplateModel).where(
            ChannelTemplateModel.store_id == store_id,
            ChannelTemplateModel.channel_id == channel_id,
            ChannelTemplateModel.name == payload.name,
            ChannelTemplateModel.language == payload.language,
        )
    )
    if existing is not None:
        raise ConflictError("A template with this name and language already exists")
    provider_body = payload.body
    for index, name in enumerate(payload.variables, start=1):
        placeholder = f"{{{{{name}}}}}"
        if placeholder not in provider_body:
            raise ConflictError(
                "Template variable is missing from the body",
                details={"variable": name},
            )
        provider_body = provider_body.replace(placeholder, f"{{{{{index}}}}}")
    unresolved = re.findall(r"\{\{([^{}]+)\}\}", provider_body)
    if unresolved and any(not value.isdigit() for value in unresolved):
        raise ConflictError(
            "Template body contains undeclared variables",
            details={"variables": unresolved},
        )
    external_id: str | None = None
    provider_status = "approved"
    if channel.mode == ChannelMode.LIVE.value:
        if client is None:
            raise ConflictError("WhatsApp template provider is unavailable")
        credentials = _credentials(session, channel, secret_key)
        result = client.create_template(
            credentials.get("access_token", ""),
            credentials.get("waba_id", ""),
            {
                "name": payload.name,
                "language": payload.language,
                "category": payload.category,
                "components": [{"type": "BODY", "text": provider_body}],
            },
        )
        external_id = str(result.get("id", "")) or None
        provider_status = str(result.get("status", "PENDING")).casefold()
    row = ChannelTemplateModel(
        store_id=store_id,
        channel_id=channel_id,
        name=payload.name,
        language=payload.language,
        body=payload.body,
        variables_json=payload.variables,
        external_id=external_id,
        category=payload.category,
        status=provider_status,
        last_synced_at=datetime.now(UTC),
    )
    session.add(row)
    session.flush()
    return _template_out(row)


def sync_templates(
    session: Session,
    store_id: str,
    channel_id: int,
    client: WhatsAppManagementClient,
    secret_key: str,
) -> list[WhatsAppTemplateOut]:
    channel = session.scalar(
        select(ChannelModel).where(
            ChannelModel.id == channel_id,
            ChannelModel.store_id == store_id,
            ChannelModel.channel_type == ChannelType.WHATSAPP.value,
        )
    )
    if channel is None:
        raise NotFoundError(details={"entity": "channel"})
    if channel.mode != ChannelMode.LIVE.value:
        return list_templates(session, store_id, channel_id)
    credentials = _credentials(session, channel, secret_key)
    now = datetime.now(UTC)
    for item in client.list_templates(
        credentials.get("access_token", ""),
        credentials.get("waba_id", ""),
    ):
        name = str(item.get("name", ""))
        language = str(item.get("language", ""))
        if not name or not language:
            continue
        row = session.scalar(
            select(ChannelTemplateModel).where(
                ChannelTemplateModel.store_id == store_id,
                ChannelTemplateModel.channel_id == channel_id,
                ChannelTemplateModel.name == name,
                ChannelTemplateModel.language == language,
            )
        )
        components = item.get("components", [])
        provider_body = next(
            (
                str(component.get("text", ""))
                for component in components
                if isinstance(component, dict) and component.get("type") == "BODY"
            ),
            "",
        )
        if row is None:
            variables = sorted(
                set(re.findall(r"\{\{(\d+)\}\}", provider_body)),
                key=int,
            )
            row = ChannelTemplateModel(
                store_id=store_id,
                channel_id=channel_id,
                name=name,
                language=language,
                body=provider_body,
                variables_json=[f"var{value}" for value in variables],
            )
            session.add(row)
        row.external_id = str(item.get("id", "")) or row.external_id
        row.category = str(item.get("category", "UTILITY"))
        row.status = str(item.get("status", "PENDING")).casefold()
        row.rejection_reason = str(item.get("rejected_reason", "")) or None
        quality = item.get("quality_score")
        row.quality_score = (
            str(quality.get("score", "")) if isinstance(quality, dict) else str(quality or "")
        ) or None
        row.last_synced_at = now
    session.flush()
    return list_templates(session, store_id, channel_id)


def webhook_credentials(
    session: Session, channel_id: int, secret_key: str
) -> tuple[ChannelModel, dict[str, str]]:
    channel = session.scalar(
        select(ChannelModel).where(
            ChannelModel.id == channel_id,
            ChannelModel.channel_type == ChannelType.WHATSAPP.value,
            ChannelModel.is_active.is_(True),
        )
    )
    if channel is None:
        raise NotFoundError(details={"entity": "whatsapp_channel"})
    return channel, _credentials(session, channel, secret_key)


def verify_signature(raw_body: bytes, signature: str | None, app_secret: str) -> None:
    if not signature or not signature.startswith("sha256=") or not app_secret:
        raise AuthorizationError("Invalid WhatsApp webhook signature")
    expected = (
        "sha256=" + hmac.new(app_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    )
    if not hmac.compare_digest(signature, expected):
        raise AuthorizationError("Invalid WhatsApp webhook signature")


def _message_text(message: dict[str, Any]) -> tuple[str, list[dict[str, str]]]:
    message_type = str(message.get("type", ""))
    if message_type == "text":
        return str(message.get("text", {}).get("body", "")), []
    if message_type in {"image", "document", "audio"}:
        media = message.get(message_type, {})
        caption = str(media.get("caption", "")).strip()
        filename = str(media.get("filename", "")).strip()
        return caption or f"[WhatsApp {message_type}]", [
            {
                "type": message_type,
                "external_id": str(media.get("id", "")),
                "mime_type": str(media.get("mime_type", "")),
                "filename": filename,
            }
        ]
    if message_type == "interactive":
        interactive = message.get("interactive", {})
        reply = interactive.get("button_reply") or interactive.get("list_reply") or {}
        return str(reply.get("title", reply.get("id", ""))), []
    return f"[Unsupported WhatsApp message: {message_type or 'unknown'}]", []


def _apply_consent(session: Session, customer: CustomerModel, text: str) -> None:
    normalized = " ".join(text.casefold().split())
    consent = dict(customer.consent_json)
    if normalized in OPT_OUT_WORDS:
        consent[ChannelType.WHATSAPP.value] = False
        customer.tags_json = sorted(set(customer.tags_json) | {"do-not-contact"})
        status = "opted_out"
    elif normalized in OPT_IN_WORDS:
        consent[ChannelType.WHATSAPP.value] = True
        customer.tags_json = [tag for tag in customer.tags_json if tag != "do-not-contact"]
        status = "opted_in"
    else:
        return
    customer.consent_json = consent
    session.add(
        CustomerConsentModel(
            store_id=customer.store_id,
            customer_id=customer.id,
            channel_type=ChannelType.WHATSAPP.value,
            status=status,
            source="inbound_keyword",
            consent_text=text[:1000],
        )
    )


def _claim_webhook_event(
    session: Session,
    *,
    store_id: str,
    account_id: str,
    event_id: str,
    event_type: str,
) -> bool:
    try:
        with session.begin_nested():
            session.add(
                ProviderWebhookEventModel(
                    store_id=store_id,
                    provider="whatsapp",
                    external_account_id=account_id,
                    external_event_id=event_id,
                    event_type=event_type,
                )
            )
            session.flush()
        return True
    except IntegrityError:
        return False


def _update_status(
    session: Session, store_id: str, external_id: str, status: str, error: str | None
) -> None:
    if status not in {
        MessageStatus.SENT.value,
        MessageStatus.DELIVERED.value,
        MessageStatus.READ.value,
        MessageStatus.FAILED.value,
    }:
        return
    message = session.scalar(
        select(MessageModel)
        .join(ConversationModel, MessageModel.conversation_id == ConversationModel.id)
        .where(
            ConversationModel.store_id == store_id,
            MessageModel.external_id == external_id,
        )
    )
    if message is None:
        return
    current_rank = STATUS_ORDER.get(message.status, -1)
    next_rank = STATUS_ORDER[status]
    if status == MessageStatus.FAILED.value or next_rank >= current_rank:
        message.status = status
        message.error_message = error


def process_webhook(
    session: Session,
    channel: ChannelModel,
    payload: dict[str, Any],
    media_loader: Callable[[str], tuple[str, str]] | None = None,
    expected_phone_number_id: str | None = None,
) -> int:
    processed = 0
    expected_phone = (expected_phone_number_id or "").strip()
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            phone_number_id = str(value.get("metadata", {}).get("phone_number_id", ""))
            if expected_phone and phone_number_id != expected_phone:
                continue
            for status_data in value.get("statuses", []):
                external_id = str(status_data.get("id", ""))
                status_value = str(status_data.get("status", ""))
                if not external_id or not _claim_webhook_event(
                    session,
                    store_id=channel.store_id,
                    account_id=phone_number_id,
                    event_id=f"{external_id}:{status_value}",
                    event_type="message_status",
                ):
                    continue
                errors = status_data.get("errors", [])
                error = str(errors[0].get("code", "")) if errors else None
                _update_status(
                    session,
                    channel.store_id,
                    external_id,
                    status_value,
                    error,
                )
                processed += 1
            contacts = {
                str(item.get("wa_id", "")): str(item.get("profile", {}).get("name", ""))
                for item in value.get("contacts", [])
            }
            for message in value.get("messages", []):
                provider_message_id = str(message.get("id", ""))
                if not provider_message_id or not _claim_webhook_event(
                    session,
                    store_id=channel.store_id,
                    account_id=phone_number_id,
                    event_id=provider_message_id,
                    event_type="inbound_message",
                ):
                    continue
                external_user_id = str(message.get("from", ""))
                text, attachments = _message_text(message)
                if media_loader is not None:
                    for attachment in attachments:
                        media_id = attachment.get("external_id", "")
                        if media_id:
                            url, mime_type = media_loader(media_id)
                            attachment["url"] = url
                            attachment["mime_type"] = mime_type
                conversation, stored = ingest_inbound_message(
                    session,
                    store_id=channel.store_id,
                    channel_type=ChannelType.WHATSAPP,
                    external_user_id=external_user_id,
                    text=text,
                    display_name=contacts.get(external_user_id, ""),
                    phone=external_user_id,
                    external_message_id=provider_message_id,
                    metadata={
                        "whatsapp_type": str(message.get("type", "")),
                        "phone_number_id": phone_number_id,
                    },
                )
                stored.attachments_json = attachments
                customer = session.get(CustomerModel, conversation.customer_id)
                if customer is not None:
                    _apply_consent(session, customer, text)
                processed += 1
    session.flush()
    return processed
