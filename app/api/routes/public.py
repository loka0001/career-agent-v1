"""Public website endpoints authenticated by store API keys (widget + connectors)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, Query, Request, status

from app.api.dependencies import ContainerDependency, DatabaseDependency
from app.api.routes.sales import build_assist_use_case
from app.db.models import ApiKeyModel, EventModel, MessageModel
from app.domain.enums import ChannelType, MessageDirection, MessageSenderType, MessageStatus
from app.domain.models import (
    PublicCatalogItem,
    PublicChatInput,
    PublicChatResponse,
    TrackEventInput,
    TrackEventsBatchInput,
)
from app.repositories.product_repository import ProductRepository
from app.services.ai_usage import record_ai_operation
from app.services.api_keys import (
    CATALOG_SCOPE,
    EVENTS_SCOPE,
    WIDGET_SCOPE,
    authorize_publishable_origin,
)
from app.services.billing import check_and_increment, require_feature
from app.services.conversations import ingest_inbound_message
from app.services.rate_limits import enforce_rate_limit

router = APIRouter(prefix="/public", tags=["public"])

ApiKeyHeader = Annotated[str | None, Header(alias="X-Api-Key")]
ApiKeyQuery = Annotated[str | None, Query(alias="key")]


def _authorize(
    container: ContainerDependency,
    api_key: str | None,
    query_key: str | None,
    origin: str | None,
    scope: str,
    *,
    max_requests: int,
    client_ip: str | None = None,
    client_fingerprint: str | None = None,
) -> ApiKeyModel:
    with container.session_factory.begin() as limiter_db:
        key = authorize_publishable_origin(
            limiter_db,
            api_key or query_key or "",
            origin,
            scope=scope,
        )
        enforce_rate_limit(
            limiter_db,
            f"public:{scope}:{key.id}",
            max_requests=max_requests,
            window_seconds=60,
        )
        if client_ip is not None and client_fingerprint is not None:
            enforce_rate_limit(
                limiter_db,
                f"public-client-ip:{scope}:{key.id}:{client_ip}",
                max_requests=12,
                window_seconds=60,
            )
            enforce_rate_limit(
                limiter_db,
                f"public-client-fingerprint:{scope}:{key.id}:{client_ip}:{client_fingerprint}",
                max_requests=12,
                window_seconds=60,
            )
        limiter_db.expunge(key)
        return key


@router.post(
    "/chat",
    response_model=PublicChatResponse,
    summary="Website widget chat: grounded assistant reply plus inbox capture",
)
def public_chat(
    payload: PublicChatInput,
    request: Request,
    container: ContainerDependency,
    db: DatabaseDependency,
    api_key: ApiKeyHeader = None,
    query_key: ApiKeyQuery = None,
    origin: Annotated[str | None, Header(alias="Origin")] = None,
    client_fingerprint: Annotated[
        str | None, Header(alias="X-Client-Fingerprint")
    ] = None,
) -> PublicChatResponse:
    client_ip = request.client.host if request.client else "unknown"
    fingerprint = (client_fingerprint or payload.session_key).strip()[:128]
    key = _authorize(
        container,
        api_key,
        query_key,
        origin,
        WIDGET_SCOPE,
        max_requests=30,
        client_ip=client_ip,
        client_fingerprint=fingerprint,
    )
    require_feature(db, key.store_id, "website_widget")
    check_and_increment(db, key.store_id, "ai_operations")
    conversation, _ = ingest_inbound_message(
        db,
        store_id=key.store_id,
        channel_type=ChannelType.WEBCHAT,
        external_user_id=payload.session_key,
        text=payload.message,
        display_name=payload.customer_name,
        metadata={"page_url": payload.page_url} if payload.page_url else None,
    )
    response = build_assist_use_case(container, db).execute(key.store_id, payload.message)
    assistant_message = MessageModel(
        conversation_id=conversation.id,
        direction=MessageDirection.OUTBOUND.value,
        sender_type=MessageSenderType.ASSISTANT.value,
        body=response.reply,
        status=MessageStatus.SENT.value,
        metadata_json={"citations": response.citations},
    )
    db.add(assistant_message)
    conversation.last_message_preview = response.reply[:140]
    conversation.unread_count = 0
    conversation.last_outbound_at = assistant_message.created_at
    conversation.sla_due_at = None
    db.flush()
    record_ai_operation(
        db,
        key.store_id,
        "website_chat",
        container.settings.ai_provider,
        container.settings.openai_model,
        ai_provider=container.ai_provider,
    )
    return PublicChatResponse(
        conversation_id=conversation.id,
        reply=response.reply,
        recommendations=response.recommendations,
        citations=response.citations,
        insufficient_context=response.insufficient_context,
    )


@router.post(
    "/events",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Track website events (single or batch)",
)
def track_events(
    payload: TrackEventInput | TrackEventsBatchInput,
    container: ContainerDependency,
    db: DatabaseDependency,
    api_key: ApiKeyHeader = None,
    query_key: ApiKeyQuery = None,
    origin: Annotated[str | None, Header(alias="Origin")] = None,
) -> dict[str, int]:
    key = _authorize(
        container, api_key, query_key, origin, EVENTS_SCOPE, max_requests=240
    )
    require_feature(db, key.store_id, "website_widget")
    events = payload.events if isinstance(payload, TrackEventsBatchInput) else [payload]
    stored = 0
    for event in events:
        if not event.consented and event.event_type.value != "purchase":
            # Without consent we only keep aggregate-safe purchase confirmations.
            continue
        db.add(
            EventModel(
                store_id=key.store_id,
                session_key=event.session_key,
                event_type=event.event_type.value,
                product_id=event.product_id,
                payload_json=dict(event.payload),
                consented=event.consented,
            )
        )
        stored += 1
    db.flush()
    return {"accepted": stored}


@router.get(
    "/catalog",
    response_model=list[PublicCatalogItem],
    summary="Active catalog for website connectors (Generic REST)",
)
def public_catalog(
    container: ContainerDependency,
    db: DatabaseDependency,
    api_key: ApiKeyHeader = None,
    query_key: ApiKeyQuery = None,
    origin: Annotated[str | None, Header(alias="Origin")] = None,
) -> list[PublicCatalogItem]:
    key = _authorize(
        container, api_key, query_key, origin, CATALOG_SCOPE, max_requests=240
    )
    require_feature(db, key.store_id, "website_widget")
    require_feature(db, key.store_id, "catalog")
    products = ProductRepository(db).list(key.store_id, active_only=True)
    return [
        PublicCatalogItem(
            product_id=item.product_id,
            name=item.name,
            category=item.category,
            price=item.price,
            stock=item.stock,
            description=item.description,
            image_url=item.public_image_url or item.original_image_url,
        )
        for item in products
    ]
