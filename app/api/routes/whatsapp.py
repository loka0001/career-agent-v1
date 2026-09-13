"""WhatsApp Business settings, templates, and public signed webhooks."""

from __future__ import annotations

import hmac
import json
import secrets
from typing import Annotated, Any

from fastapi import APIRouter, File, Form, Header, Query, Request, Response, UploadFile, status

from app.api.dependencies import (
    AdminReadUser,
    AdminUser,
    ContainerDependency,
    DatabaseDependency,
)
from app.api.request_body import read_bounded_body
from app.db.models import ChannelTemplateModel
from app.domain.enums import ChannelMode, MessageSenderType
from app.domain.errors import (
    AuthorizationError,
    ConflictError,
    IntegrationNotConfiguredError,
    InvalidInputError,
)
from app.domain.models import (
    MessageOut,
    TemplateReplyInput,
    WhatsAppConnectionCheck,
    WhatsAppEmbeddedConnectInput,
    WhatsAppEmbeddedExchangeInput,
    WhatsAppEmbeddedExchangeOut,
    WhatsAppEmbeddedStartOut,
    WhatsAppPhoneOption,
    WhatsAppSettingsInput,
    WhatsAppSettingsStatus,
    WhatsAppTemplateInput,
    WhatsAppTemplateOut,
)
from app.integrations.whatsapp import WhatsAppManagementClient
from app.repositories.inbox_repository import InboxRepository
from app.repositories.provider_connection_repository import OAuthTransactionRepository
from app.services.conversations import queue_outbound_message
from app.services.whatsapp import (
    create_template,
    get_settings_status,
    list_templates,
    process_webhook,
    refresh_connection_health,
    save_settings,
    sync_templates,
    verify_signature,
    webhook_credentials,
)

router = APIRouter(prefix="/integrations/whatsapp", tags=["whatsapp"])
webhook_router = APIRouter(prefix="/webhooks/whatsapp", tags=["whatsapp-webhook"])


def _management(container: ContainerDependency) -> WhatsAppManagementClient:
    return WhatsAppManagementClient(
        container.settings.meta_graph_api_base,
        container.settings.meta_graph_api_version,
        container.settings.meta_request_timeout_seconds,
    )


@router.get("", response_model=WhatsAppSettingsStatus)
def settings_status(
    user: AdminReadUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> WhatsAppSettingsStatus:
    return get_settings_status(
        db,
        user.store_id,
        container.settings.effective_secret_key,
        demo_available=container.settings.demo_mode,
        embedded_signup_available=bool(
            container.settings.meta_app_id
            and container.settings.meta_app_secret.get_secret_value()
            and container.settings.meta_whatsapp_config_id
        ),
    )


@router.put("", response_model=WhatsAppSettingsStatus)
def update_settings(
    payload: WhatsAppSettingsInput,
    user: AdminUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> WhatsAppSettingsStatus:
    if payload.mode == ChannelMode.DEMO and not container.settings.demo_mode:
        raise ConflictError("Demo channel mode is disabled")
    return save_settings(
        db,
        user.store_id,
        payload,
        container.settings.effective_secret_key,
        demo_available=container.settings.demo_mode,
    )


@router.post("/embedded/start", response_model=WhatsAppEmbeddedStartOut)
def start_embedded_signup(
    user: AdminUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> WhatsAppEmbeddedStartOut:
    settings = container.settings
    if not all(
        (
            settings.meta_app_id,
            settings.meta_app_secret.get_secret_value(),
            settings.meta_whatsapp_config_id,
        )
    ):
        raise IntegrationNotConfiguredError("WhatsApp Embedded Signup is not configured")
    _, state = OAuthTransactionRepository(db).create(
        provider="whatsapp",
        store_id=user.store_id,
        user_id=user.user_id,
    )
    return WhatsAppEmbeddedStartOut(
        app_id=settings.meta_app_id,
        config_id=settings.meta_whatsapp_config_id,
        api_version=settings.meta_graph_api_version,
        state=state,
        solution_id=settings.meta_whatsapp_solution_id or None,
    )


@router.post("/embedded/exchange", response_model=WhatsAppEmbeddedExchangeOut)
def exchange_embedded_signup(
    payload: WhatsAppEmbeddedExchangeInput,
    user: AdminUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> WhatsAppEmbeddedExchangeOut:
    settings = container.settings
    transactions = OAuthTransactionRepository(db)
    transaction = transactions.consume(
        state=payload.state,
        provider="whatsapp",
        store_id=user.store_id,
        user_id=user.user_id,
    )
    client = _management(container)
    access_token = client.exchange_code(
        payload.code,
        settings.meta_app_id,
        settings.meta_app_secret.get_secret_value(),
    )
    waba_ids = (
        [payload.waba_id]
        if payload.waba_id
        else client.discover_waba_ids(
            access_token,
            settings.meta_app_id,
            settings.meta_app_secret.get_secret_value(),
        )
    )
    phones = [
        phone for waba_id in waba_ids for phone in client.list_phone_numbers(access_token, waba_id)
    ]
    if not phones:
        raise ConflictError("No WhatsApp phone number was granted by Meta")
    transactions.store_exchange_result(
        transaction,
        credentials={"access_token": access_token},
        metadata={"phones": phones},
    )
    return WhatsAppEmbeddedExchangeOut(
        transaction_id=transaction.id,
        phones=[WhatsAppPhoneOption.model_validate(phone) for phone in phones],
    )


@router.post("/embedded/connect", response_model=WhatsAppSettingsStatus)
def connect_embedded_signup(
    payload: WhatsAppEmbeddedConnectInput,
    user: AdminUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> WhatsAppSettingsStatus:
    transactions = OAuthTransactionRepository(db)
    transaction, credentials = transactions.pending_result(
        transaction_id=payload.transaction_id,
        provider="whatsapp",
        store_id=user.store_id,
        user_id=user.user_id,
    )
    options = transaction.result_metadata_json.get("phones", [])
    selected = next(
        (
            item
            for item in options
            if isinstance(item, dict)
            and str(item.get("phone_number_id")) == payload.phone_number_id
            and str(item.get("waba_id")) == payload.waba_id
        ),
        None,
    )
    if selected is None:
        raise ConflictError("Selected WhatsApp number was not granted by Meta")
    client = _management(container)
    access_token = credentials.get("access_token", "")
    client.subscribe_app(access_token, payload.waba_id)
    client.register_phone(
        access_token,
        payload.phone_number_id,
        payload.registration_pin,
    )
    result = save_settings(
        db,
        user.store_id,
        WhatsAppSettingsInput(
            mode=ChannelMode.LIVE,
            display_name=str(
                selected.get("verified_name")
                or selected.get("display_phone_number")
                or "WhatsApp Business"
            ),
            phone_number_id=payload.phone_number_id,
            waba_id=payload.waba_id,
            access_token=access_token,
            app_secret=container.settings.meta_app_secret.get_secret_value(),
            verify_token=secrets.token_urlsafe(36),
            is_active=True,
        ),
        container.settings.effective_secret_key,
        demo_available=container.settings.demo_mode,
    )
    transactions.complete(transaction)
    return result


@router.post("/check", response_model=WhatsAppConnectionCheck)
def check_connection(
    user: AdminUser, container: ContainerDependency, db: DatabaseDependency
) -> WhatsAppConnectionCheck:
    channel = get_settings_status(
        db,
        user.store_id,
        container.settings.effective_secret_key,
        demo_available=container.settings.demo_mode,
    )
    if channel.channel_id is None:
        raise ConflictError("WhatsApp is not configured")
    row, credentials = webhook_credentials(
        db, channel.channel_id, container.settings.effective_secret_key
    )
    success, error = refresh_connection_health(db, row, credentials)
    return WhatsAppConnectionCheck(success=success, error_code=error)


@router.get("/templates", response_model=list[WhatsAppTemplateOut])
def templates(
    user: AdminReadUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> list[WhatsAppTemplateOut]:
    channel = get_settings_status(
        db,
        user.store_id,
        container.settings.effective_secret_key,
        demo_available=container.settings.demo_mode,
    )
    if channel.channel_id is None:
        return []
    return list_templates(db, user.store_id, channel.channel_id)


@router.post(
    "/templates",
    response_model=WhatsAppTemplateOut,
    status_code=status.HTTP_201_CREATED,
)
def add_template(
    payload: WhatsAppTemplateInput,
    user: AdminUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> WhatsAppTemplateOut:
    channel = get_settings_status(
        db,
        user.store_id,
        container.settings.effective_secret_key,
        demo_available=container.settings.demo_mode,
    )
    if channel.channel_id is None:
        raise ConflictError("WhatsApp is not configured")
    return create_template(
        db,
        user.store_id,
        channel.channel_id,
        payload,
        client=_management(container),
        secret_key=container.settings.effective_secret_key,
    )


@router.post("/templates/sync", response_model=list[WhatsAppTemplateOut])
def synchronize_templates(
    user: AdminUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> list[WhatsAppTemplateOut]:
    channel = get_settings_status(
        db,
        user.store_id,
        container.settings.effective_secret_key,
        demo_available=container.settings.demo_mode,
    )
    if channel.channel_id is None:
        raise ConflictError("WhatsApp is not configured")
    return sync_templates(
        db,
        user.store_id,
        channel.channel_id,
        _management(container),
        container.settings.effective_secret_key,
    )


@router.post(
    "/conversations/{conversation_id}/template",
    response_model=MessageOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def send_template(
    conversation_id: int,
    payload: TemplateReplyInput,
    user: AdminUser,
    db: DatabaseDependency,
) -> MessageOut:
    repository = InboxRepository(db)
    conversation = repository.get_conversation_row(user.store_id, conversation_id)
    template = db.get(ChannelTemplateModel, payload.template_id)
    if template is None or template.store_id != user.store_id:
        raise ConflictError("WhatsApp template is unavailable")
    text = template.body
    for name, value in payload.variables.items():
        text = text.replace(f"{{{{{name}}}}}", value)
    message = queue_outbound_message(
        db,
        store_id=user.store_id,
        conversation=conversation,
        text=text,
        sender_type=MessageSenderType.AGENT,
        sender_user_id=user.user_id,
        template=template,
        template_variables=payload.variables,
    )
    return MessageOut.model_validate(message, from_attributes=True)


@router.post(
    "/conversations/{conversation_id}/media",
    response_model=MessageOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def send_media(
    conversation_id: int,
    user: AdminUser,
    container: ContainerDependency,
    db: DatabaseDependency,
    media: Annotated[UploadFile, File()],
    caption: Annotated[str, Form(max_length=2000)] = "",
) -> MessageOut:
    allowed = {
        "image/jpeg": "image",
        "image/png": "image",
        "application/pdf": "document",
        "text/plain": "document",
        "audio/aac": "audio",
        "audio/mp4": "audio",
        "audio/mpeg": "audio",
        "audio/amr": "audio",
        "audio/ogg": "audio",
    }
    mime_type = (media.content_type or "").split(";", 1)[0]
    media_type = allowed.get(mime_type)
    if media_type is None:
        raise InvalidInputError("Unsupported WhatsApp media type")
    content = await media.read(container.settings.max_channel_media_bytes + 1)
    if len(content) > container.settings.max_channel_media_bytes:
        raise InvalidInputError("WhatsApp media exceeds the configured size limit")
    container.malware_scanner.scan(content)
    conversation = InboxRepository(db).get_conversation_row(user.store_id, conversation_id)
    stored = container.image_storage.store_media(
        content,
        mime_type,
        store_id=user.store_id,
    )
    message = queue_outbound_message(
        db,
        store_id=user.store_id,
        conversation=conversation,
        text=caption or f"[WhatsApp {media_type}]",
        sender_type=MessageSenderType.AGENT,
        sender_user_id=user.user_id,
        attachments=[
            {
                "type": media_type,
                "url": stored.public_url or stored.original_url,
                "mime_type": mime_type,
                "filename": media.filename or "",
            }
        ],
    )
    return MessageOut.model_validate(message, from_attributes=True)


@webhook_router.get("/{channel_id}")
def verify_webhook(
    channel_id: int,
    container: ContainerDependency,
    db: DatabaseDependency,
    mode: Annotated[str | None, Query(alias="hub.mode")] = None,
    verify_token: Annotated[str | None, Query(alias="hub.verify_token")] = None,
    challenge: Annotated[str | None, Query(alias="hub.challenge")] = None,
) -> Response:
    _, credentials = webhook_credentials(db, channel_id, container.settings.effective_secret_key)
    expected = credentials.get("verify_token", "")
    if (
        mode != "subscribe"
        or not verify_token
        or not expected
        or not hmac.compare_digest(verify_token, expected)
    ):
        raise AuthorizationError("Invalid WhatsApp webhook verification token")
    return Response(content=challenge or "", media_type="text/plain")


@webhook_router.post("/{channel_id}")
async def receive_webhook(
    channel_id: int,
    request: Request,
    container: ContainerDependency,
    db: DatabaseDependency,
    signature: Annotated[str | None, Header(alias="X-Hub-Signature-256")] = None,
) -> dict[str, Any]:
    raw_body = await read_bounded_body(
        request,
        max_bytes=2 * 1024 * 1024,
        label="WhatsApp webhook",
    )
    channel, credentials = webhook_credentials(
        db, channel_id, container.settings.effective_secret_key
    )
    verify_signature(raw_body, signature, credentials.get("app_secret", ""))
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise InvalidInputError("Invalid WhatsApp webhook JSON") from exc
    if not isinstance(payload, dict):
        raise InvalidInputError("Invalid WhatsApp webhook payload")
    client = _management(container)

    def load_media(media_id: str) -> tuple[str, str]:
        content, mime_type = client.download_media(
            credentials.get("access_token", ""),
            media_id,
            container.settings.max_channel_media_bytes,
        )
        container.malware_scanner.scan(content)
        stored = container.image_storage.store_media(
            content,
            mime_type,
            store_id=channel.store_id,
        )
        return stored.public_url or stored.original_url, mime_type

    return {
        "received": True,
        "processed": process_webhook(
            db,
            channel,
            payload,
            media_loader=load_media,
            expected_phone_number_id=credentials.get("phone_number_id", ""),
        ),
    }
