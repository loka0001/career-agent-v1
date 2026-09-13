"""Commerce website connections, synchronization, and signed webhooks."""

from __future__ import annotations

import hashlib
import json
from typing import Annotated, Any
from urllib.parse import urlencode

from fastapi import APIRouter, Header, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.api.dependencies import AdminUser, ContainerDependency, CurrentUser, DatabaseDependency
from app.api.request_body import read_bounded_body
from app.db.models import ProviderConnectionModel
from app.domain.errors import InvalidInputError, NotFoundError
from app.domain.models import (
    CommerceConnectionInput,
    CommerceSyncResult,
    ProviderConnectionOut,
    ShopifyOAuthExchangeInput,
    ShopifyOAuthStart,
    ShopifyOAuthStartInput,
)
from app.integrations.commerce import verify_commerce_signature
from app.repositories.provider_connection_repository import ProviderConnectionRepository
from app.services.commerce_connectors import (
    claim_commerce_webhook,
    connect_commerce,
    exchange_shopify_oauth,
    start_shopify_oauth,
    sync_commerce_connection,
    verify_shopify_oauth_callback,
)

router = APIRouter(prefix="/integrations/commerce", tags=["commerce-connectors"])
webhook_router = APIRouter(prefix="/webhooks/commerce", tags=["commerce-webhooks"])
oauth_callback_router = APIRouter(prefix="/shopify/oauth", tags=["shopify-oauth"])


@router.post("", response_model=ProviderConnectionOut, status_code=status.HTTP_201_CREATED)
def connect(
    payload: CommerceConnectionInput,
    user: AdminUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> ProviderConnectionOut:
    return connect_commerce(db, container.settings, user.store_id, payload)


@router.post("/shopify/oauth/start", response_model=ShopifyOAuthStart)
def start_shopify_install(
    payload: ShopifyOAuthStartInput,
    user: AdminUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> ShopifyOAuthStart:
    return start_shopify_oauth(
        db,
        container.settings,
        user.user_id,
        user.store_id,
        payload,
    )


@router.post("/shopify/oauth/exchange", response_model=ProviderConnectionOut)
def exchange_shopify_install(
    payload: ShopifyOAuthExchangeInput,
    user: AdminUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> ProviderConnectionOut:
    return exchange_shopify_oauth(
        db,
        container.settings,
        user.user_id,
        user.store_id,
        payload,
    )


@oauth_callback_router.get("/callback")
def shopify_oauth_callback(
    code: str,
    state: str,
    shop: str,
    hmac: str,
    timestamp: str,
    user: CurrentUser,
    container: ContainerDependency,
    db: DatabaseDependency,
    host: str | None = None,
) -> RedirectResponse:
    payload = ShopifyOAuthExchangeInput(
        code=code,
        state=state,
        shop=shop,
        hmac=hmac,
        timestamp=timestamp,
        host=host,
    )
    verify_shopify_oauth_callback(
        db,
        container.settings,
        user.user_id,
        user.store_id,
        payload,
    )
    query = urlencode(
        {
            "shopify_code": code,
            "shopify_state": state,
            "shopify_shop": shop,
            "shopify_hmac": hmac,
            "shopify_timestamp": timestamp,
            **({"shopify_host": host} if host else {}),
        }
    )
    return RedirectResponse(f"/app/integrations?{query}")


@router.post("/{connection_id}/sync", response_model=CommerceSyncResult)
def synchronize(
    connection_id: str,
    user: AdminUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> CommerceSyncResult:
    return sync_commerce_connection(
        db,
        container.settings,
        user.store_id,
        connection_id,
    )


@webhook_router.post("/{connection_id}", status_code=status.HTTP_202_ACCEPTED)
async def commerce_webhook(
    connection_id: str,
    request: Request,
    db: DatabaseDependency,
    shopify_signature: Annotated[str | None, Header(alias="X-Shopify-Hmac-Sha256")] = None,
    shopify_event_id: Annotated[str | None, Header(alias="X-Shopify-Webhook-Id")] = None,
    shopify_topic: Annotated[str | None, Header(alias="X-Shopify-Topic")] = None,
    woo_signature: Annotated[str | None, Header(alias="X-WC-Webhook-Signature")] = None,
    woo_event_id: Annotated[str | None, Header(alias="X-WC-Webhook-Delivery-ID")] = None,
    woo_topic: Annotated[str | None, Header(alias="X-WC-Webhook-Topic")] = None,
    generic_signature: Annotated[str | None, Header(alias="X-Commerce-Signature")] = None,
    generic_event_id: Annotated[str | None, Header(alias="X-Commerce-Event-ID")] = None,
    generic_topic: Annotated[str | None, Header(alias="X-Commerce-Topic")] = None,
) -> dict[str, bool]:
    row = db.scalar(
        select(ProviderConnectionModel).where(
            ProviderConnectionModel.id == connection_id,
            ProviderConnectionModel.provider.in_(["shopify", "woocommerce", "generic_website"]),
        )
    )
    if row is None:
        raise NotFoundError(details={"entity": "commerce_connection"})
    credentials = ProviderConnectionRepository(db, row.store_id).credentials(row.id)
    body = await read_bounded_body(request, max_bytes=2 * 1024 * 1024, label="Commerce webhook")
    signature = (
        shopify_signature
        if row.provider == "shopify"
        else woo_signature
        if row.provider == "woocommerce"
        else generic_signature
    )
    verify_commerce_signature(
        row.provider,
        body,
        signature,
        credentials.get("webhook_secret", ""),
    )
    try:
        payload: Any = json.loads(body)
    except json.JSONDecodeError as exc:
        raise InvalidInputError("Commerce webhook JSON is invalid") from exc
    if not isinstance(payload, dict):
        raise InvalidInputError("Commerce webhook payload must be an object")
    event_type = (
        shopify_topic
        if row.provider == "shopify"
        else woo_topic
        if row.provider == "woocommerce"
        else generic_topic
    ) or "commerce.updated"
    external_event_id = (
        shopify_event_id
        if row.provider == "shopify"
        else woo_event_id
        if row.provider == "woocommerce"
        else generic_event_id
    )
    if not external_event_id:
        external_event_id = hashlib.sha256(event_type.encode() + b":" + body).hexdigest()
    claimed = claim_commerce_webhook(db, row, external_event_id, event_type)
    return {"received": True, "enqueued": claimed}
