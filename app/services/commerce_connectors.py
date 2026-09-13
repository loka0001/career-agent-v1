"""Tenant-scoped commerce connection, synchronization, and durable webhook work."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode, urlparse

import httpx
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import (
    CustomerIdentityModel,
    CustomerModel,
    ExternalOrderMappingModel,
    ExternalProductMappingModel,
    InventoryTransactionModel,
    OrderItemModel,
    OrderModel,
    OrderTransitionModel,
    ProductModel,
    ProductVariantModel,
    ProviderConnectionModel,
    ProviderWebhookEventModel,
)
from app.domain.enums import OrderStatus, ProductStatus, ProviderConnectionStatus
from app.domain.errors import (
    AuthenticationError,
    ConflictError,
    ExternalProviderError,
    IntegrationNotConfiguredError,
    InvalidInputError,
)
from app.domain.models import (
    CommerceConnectionInput,
    CommerceSyncResult,
    ProviderConnectionOut,
    ShopifyOAuthExchangeInput,
    ShopifyOAuthStart,
    ShopifyOAuthStartInput,
)
from app.integrations.commerce import (
    CommerceConnector,
    ExternalOrder,
    ExternalProduct,
    connector_for,
    validate_public_https_url,
)
from app.repositories.provider_connection_repository import (
    OAuthTransactionRepository,
    ProviderConnectionRepository,
)
from app.services.inventory import adjust_inventory
from app.services.job_queue import enqueue_job, job_handler
from app.services.provider_connections import connection_out

_SETTINGS: Settings | None = None


def configure_commerce_services(settings: Settings) -> None:
    global _SETTINGS
    _SETTINGS = settings


def _hash_payload(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()


def _local_product_id(provider: str, item: ExternalProduct) -> str:
    source = f"{provider}:{item.external_product_id}:{item.external_variant_id}"
    digest = hashlib.sha256(source.encode()).hexdigest()[:20]
    suffix = "".join(
        character for character in item.sku if character.isalnum() or character in "_-"
    )
    return f"{provider[:8]}-{suffix[:30]}-{digest}"[:64]


def _local_variant_id(item: ExternalProduct) -> str:
    source = item.external_variant_id or item.sku or "default"
    safe = "".join(character for character in source if character.isalnum() or character in "_-")
    if safe and len(safe) <= 64:
        return safe
    return f"variant-{hashlib.sha256(source.encode()).hexdigest()[:24]}"


def _connector(
    settings: Settings,
    row: ProviderConnectionModel,
    credentials: dict[str, str],
) -> CommerceConnector:
    return connector_for(
        row.provider,
        credentials,
        shopify_api_version=settings.shopify_api_version,
        timeout_seconds=settings.commerce_request_timeout_seconds,
    )


def _shopify_store_url(shop: str) -> str:
    candidate = shop.strip()
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    return validate_public_https_url(candidate, shopify=True)


def _shopify_domain(shop_url: str) -> str:
    hostname = urlparse(shop_url).hostname
    if not hostname:
        raise InvalidInputError("Shopify URL must include a hostname")
    return hostname


def _require_shopify_oauth_settings(settings: Settings) -> tuple[str, str]:
    api_key = settings.shopify_app_api_key
    api_secret = settings.shopify_app_api_secret.get_secret_value()
    if not api_key or not api_secret:
        raise IntegrationNotConfiguredError("Shopify OAuth is not configured")
    return api_key, api_secret


def _shopify_oauth_message(payload: ShopifyOAuthExchangeInput) -> str:
    params: dict[str, str] = {
        "code": payload.code,
        "shop": payload.shop,
        "state": payload.state,
        "timestamp": payload.timestamp,
    }
    if payload.host:
        params["host"] = payload.host
    return urlencode(sorted(params.items()))


def _verify_shopify_oauth_hmac(
    payload: ShopifyOAuthExchangeInput,
    api_secret: str,
) -> None:
    expected = hmac.new(
        api_secret.encode("utf-8"),
        _shopify_oauth_message(payload).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, payload.hmac):
        raise AuthenticationError("Invalid Shopify OAuth signature")


def start_shopify_oauth(
    session: Session,
    settings: Settings,
    user_id: str,
    store_id: str,
    payload: ShopifyOAuthStartInput,
) -> ShopifyOAuthStart:
    api_key, _ = _require_shopify_oauth_settings(settings)
    shop_url = _shopify_store_url(payload.shop)
    transaction, state = OAuthTransactionRepository(session).create(
        provider="shopify",
        user_id=user_id,
        store_id=store_id,
    )
    transaction.result_metadata_json = {
        "shop_url": shop_url,
        "display_name": payload.display_name,
        "install_webhooks": payload.install_webhooks,
    }
    query = urlencode(
        {
            "client_id": api_key,
            "scope": settings.shopify_oauth_scopes,
            "redirect_uri": settings.shopify_oauth_redirect_uri,
            "state": state,
        }
    )
    return ShopifyOAuthStart(
        authorization_url=f"{shop_url}/admin/oauth/authorize?{query}",
        state=state,
        shop=_shopify_domain(shop_url),
    )


def exchange_shopify_oauth(
    session: Session,
    settings: Settings,
    user_id: str,
    store_id: str,
    payload: ShopifyOAuthExchangeInput,
) -> ProviderConnectionOut:
    api_key, api_secret = _require_shopify_oauth_settings(settings)
    _verify_shopify_oauth_hmac(payload, api_secret)
    shop_url = _shopify_store_url(payload.shop)
    oauth_transactions = OAuthTransactionRepository(session)
    transaction = oauth_transactions.consume(
        state=payload.state,
        provider="shopify",
        user_id=user_id,
        store_id=store_id,
    )
    if transaction.result_metadata_json.get("shop_url") != shop_url:
        raise AuthenticationError("Shopify OAuth shop does not match state")
    try:
        token_response = httpx.post(
            f"{shop_url}/admin/oauth/access_token",
            json={
                "client_id": api_key,
                "client_secret": api_secret,
                "code": payload.code,
            },
            timeout=settings.commerce_request_timeout_seconds,
        )
        token_response.raise_for_status()
        token_body = token_response.json()
        access_token = str(token_body["access_token"])
        granted_scopes = str(token_body.get("scope") or settings.shopify_oauth_scopes)
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        raise ExternalProviderError("Shopify OAuth exchange failed") from exc
    connection = connect_commerce(
        session,
        settings,
        store_id,
        CommerceConnectionInput(
            provider="shopify",
            display_name=str(transaction.result_metadata_json.get("display_name") or "Shopify"),
            store_url=shop_url,
            access_token=access_token,
            webhook_secret=api_secret,
            install_webhooks=bool(transaction.result_metadata_json.get("install_webhooks", True)),
        ),
    )
    row = ProviderConnectionRepository(session, store_id).get(connection.id)
    row.scopes_json = sorted(
        {scope.strip() for scope in granted_scopes.split(",") if scope.strip()}
    )
    metadata = dict(row.metadata_json)
    metadata["oauth_installation"] = True
    metadata["oauth_scopes"] = row.scopes_json
    metadata["webhook_secret_source"] = "shopify_app_api_secret"
    row.metadata_json = metadata
    session.flush()
    oauth_transactions.complete(transaction)
    return connection_out(row)


def verify_shopify_oauth_callback(
    session: Session,
    settings: Settings,
    user_id: str,
    store_id: str,
    payload: ShopifyOAuthExchangeInput,
) -> None:
    _, api_secret = _require_shopify_oauth_settings(settings)
    _verify_shopify_oauth_hmac(payload, api_secret)
    shop_url = _shopify_store_url(payload.shop)
    transaction = OAuthTransactionRepository(session).validate(
        state=payload.state,
        provider="shopify",
        user_id=user_id,
        store_id=store_id,
    )
    if transaction.result_metadata_json.get("shop_url") != shop_url:
        raise AuthenticationError("Shopify OAuth shop does not match state")


def connect_commerce(
    session: Session,
    settings: Settings,
    store_id: str,
    payload: CommerceConnectionInput,
) -> ProviderConnectionOut:
    credentials = {
        "store_url": payload.store_url,
        "access_token": payload.access_token,
        "consumer_key": payload.consumer_key,
        "consumer_secret": payload.consumer_secret,
        "webhook_secret": payload.webhook_secret,
    }
    required = (
        ("access_token", "webhook_secret")
        if payload.provider == "shopify"
        else ("consumer_key", "consumer_secret")
        if payload.provider == "woocommerce"
        else ("access_token",)
    )
    missing = [name for name in required if not credentials.get(name)]
    if missing:
        raise InvalidInputError(
            "Commerce connection credentials are incomplete",
            details={"missing": missing},
        )
    if not credentials["webhook_secret"]:
        credentials["webhook_secret"] = secrets.token_urlsafe(48)
    connector = connector_for(
        payload.provider,
        credentials,
        shopify_api_version=settings.shopify_api_version,
        timeout_seconds=settings.commerce_request_timeout_seconds,
    )
    normalized_url = connector.store_url  # type: ignore[attr-defined]
    credentials["store_url"] = normalized_url
    repository = ProviderConnectionRepository(session, store_id)
    row = repository.upsert(
        provider=payload.provider,
        connection_type="store" if payload.provider != "generic_website" else "site",
        external_resource_id=normalized_url,
        display_name=payload.display_name,
        credentials=credentials,
        scopes=["catalog:read", "orders:read", "webhooks:manage"],
        metadata={
            "mode": "live",
            "webhooks_requested": payload.install_webhooks,
            "api_version": (
                settings.shopify_api_version if payload.provider == "shopify" else "v3"
            ),
        },
        status=ProviderConnectionStatus.PENDING,
    )
    try:
        external_id, provider_name = connector.check_connection()
        row.external_account_id = external_id
        row.display_name = payload.display_name or provider_name
        if payload.install_webhooks:
            connector.install_webhooks(
                f"{settings.public_base_url.rstrip('/')}/webhooks/commerce/{row.id}",
                credentials["webhook_secret"],
            )
    except ExternalProviderError as exc:
        row.status = ProviderConnectionStatus.DEGRADED.value
        row.last_error_code = "provider_connection_failed"
        row.last_error_message = str(exc)[:500]
    else:
        row.status = ProviderConnectionStatus.CONNECTED.value
        row.last_error_code = None
        row.last_error_message = None
    row.last_health_at = datetime.now(UTC)
    session.flush()
    return connection_out(row)


def _upsert_product(
    session: Session,
    row: ProviderConnectionModel,
    item: ExternalProduct,
) -> str:
    mapping = session.scalar(
        select(ExternalProductMappingModel).where(
            ExternalProductMappingModel.store_id == row.store_id,
            ExternalProductMappingModel.provider_connection_id == row.id,
            ExternalProductMappingModel.external_product_id == item.external_product_id,
            ExternalProductMappingModel.external_variant_id == item.external_variant_id,
        )
    )
    payload_hash = _hash_payload(item.raw)
    created = mapping is None
    if mapping is not None and mapping.payload_hash == payload_hash:
        return "unchanged"
    product = session.get(ProductModel, mapping.product_pk) if mapping else None
    if product is None:
        product = ProductModel(
            store_id=row.store_id,
            product_id=_local_product_id(row.provider, item),
            name=item.name,
            category=item.category or row.provider,
            sku=item.sku or _local_product_id(row.provider, item),
            price_numeric=max(item.price, Decimal("0.01")),
            stock=item.stock,
            images_json=[item.image_url] if item.image_url else [],
            source_of_truth="external",
            source_provider=row.provider,
            features_json=[],
            benefits_json=[],
            description=item.description or item.name,
            image_summary="",
            original_image_url=item.image_url,
            public_image_url=item.image_url or None,
            status=ProductStatus.ACTIVE.value if item.active else ProductStatus.DRAFT.value,
        )
        session.add(product)
        session.flush()
        created_variant = ProductVariantModel(
            store_id=row.store_id,
            product_pk=product.id,
            variant_id=_local_variant_id(item),
            title=item.name,
            sku=item.sku or product.product_id,
            price_numeric=product.price_numeric,
            stock=item.stock,
            status="active" if item.active else "draft",
        )
        session.add(created_variant)
        session.flush()
        if item.stock:
            session.add(
                InventoryTransactionModel(
                    store_id=row.store_id,
                    product_pk=product.id,
                    variant_pk=created_variant.id,
                    delta=item.stock,
                    quantity_before=0,
                    quantity_after=item.stock,
                    reason="external_reconciliation",
                    reference_type=row.provider,
                    reference_id=item.external_inventory_id or item.external_variant_id,
                    idempotency_key=f"sync:{row.id}:{payload_hash}",
                )
            )
        mapping = ExternalProductMappingModel(
            store_id=row.store_id,
            provider_connection_id=row.id,
            product_pk=product.id,
            external_product_id=item.external_product_id,
            external_variant_id=item.external_variant_id,
            external_sku=item.sku,
            external_inventory_id=item.external_inventory_id,
            payload_hash=payload_hash,
        )
        session.add(mapping)
    else:
        assert mapping is not None
        product.name = item.name
        product.category = item.category or row.provider
        product.price_numeric = max(item.price, Decimal("0.01"))
        product.description = item.description or item.name
        product.original_image_url = item.image_url
        product.public_image_url = item.image_url or None
        product.status = ProductStatus.ACTIVE.value if item.active else ProductStatus.DRAFT.value
        product.sku = item.sku or product.sku
        product.images_json = [item.image_url] if item.image_url else product.images_json
        product.source_of_truth = "external"
        product.source_provider = row.provider
        variant_id = _local_variant_id(item)
        sync_variant = session.scalar(
            select(ProductVariantModel).where(
                ProductVariantModel.store_id == row.store_id,
                ProductVariantModel.product_pk == product.id,
                ProductVariantModel.variant_id == variant_id,
            )
        )
        if sync_variant is None:
            sync_variant = ProductVariantModel(
                store_id=row.store_id,
                product_pk=product.id,
                variant_id=variant_id,
                title=item.name,
                sku=item.sku or product.product_id,
                price_numeric=product.price_numeric,
                stock=0,
                status="active" if item.active else "draft",
            )
            session.add(sync_variant)
            session.flush()
        sync_variant.title = item.name
        sync_variant.sku = item.sku or sync_variant.sku
        sync_variant.price_numeric = product.price_numeric
        sync_variant.status = "active" if item.active else "draft"
        adjust_inventory(
            session,
            store_id=row.store_id,
            product_id=product.product_id,
            variant_id=sync_variant.variant_id,
            delta=item.stock - sync_variant.stock,
            reason="external_reconciliation",
            idempotency_key=f"sync:{row.id}:{payload_hash}",
            reference_type=row.provider,
            reference_id=item.external_inventory_id or item.external_variant_id,
            allow_negative=False,
        )
        product.updated_at = datetime.now(UTC)
        mapping.external_inventory_id = item.external_inventory_id
        mapping.external_sku = item.sku
        mapping.payload_hash = payload_hash
    mapping.source_updated_at = item.updated_at
    mapping.updated_at = datetime.now(UTC)
    session.flush()
    return "created" if created else "updated"


def _customer_for_order(
    session: Session,
    row: ProviderConnectionModel,
    order: ExternalOrder,
) -> CustomerModel:
    identity_value = order.customer_external_id or order.customer_email or order.customer_phone
    if not identity_value:
        identity_value = f"order:{order.external_order_id}"
    external_id = f"{row.provider}:{identity_value}"
    if len(external_id) > 160:
        external_id = f"{row.provider}:{hashlib.sha256(external_id.encode()).hexdigest()}"
    identity = session.scalar(
        select(CustomerIdentityModel).where(
            CustomerIdentityModel.store_id == row.store_id,
            CustomerIdentityModel.channel_type == "webchat",
            CustomerIdentityModel.external_id == external_id,
        )
    )
    if identity is not None:
        customer = session.get(CustomerModel, identity.customer_id)
        if customer is None:
            raise ConflictError("External customer identity is invalid")
    else:
        customer = CustomerModel(
            store_id=row.store_id,
            display_name=order.customer_name,
            email=order.customer_email or None,
            phone=order.customer_phone or None,
            attributes_json={"source": row.provider},
        )
        session.add(customer)
        session.flush()
        session.add(
            CustomerIdentityModel(
                store_id=row.store_id,
                customer_id=customer.id,
                channel_type="webchat",
                external_id=external_id,
            )
        )
    customer.display_name = order.customer_name or customer.display_name
    customer.email = order.customer_email or customer.email
    customer.phone = order.customer_phone or customer.phone
    customer.last_seen_at = datetime.now(UTC)
    session.flush()
    return customer


def _order_status(value: str) -> OrderStatus:
    try:
        return OrderStatus(value)
    except ValueError:
        return OrderStatus.PENDING


def _payment_status_for_order(status: OrderStatus) -> str:
    if status in {
        OrderStatus.PAID,
        OrderStatus.PROCESSING,
        OrderStatus.SHIPPED,
        OrderStatus.DELIVERED,
    }:
        return "paid"
    if status == OrderStatus.REFUNDED:
        return "refunded"
    if status == OrderStatus.CANCELLED:
        return "cancelled"
    return "unpaid"


def _fulfillment_status_for_order(status: OrderStatus) -> str:
    return {
        OrderStatus.PROCESSING: "processing",
        OrderStatus.SHIPPED: "shipped",
        OrderStatus.DELIVERED: "fulfilled",
        OrderStatus.CANCELLED: "cancelled",
    }.get(status, "unfulfilled")


def _mapped_product(
    session: Session,
    row: ProviderConnectionModel,
    variant_id: str,
    sku: str,
) -> ProductModel | None:
    mapping = None
    if variant_id:
        mapping = session.scalar(
            select(ExternalProductMappingModel).where(
                ExternalProductMappingModel.store_id == row.store_id,
                ExternalProductMappingModel.provider_connection_id == row.id,
                ExternalProductMappingModel.external_variant_id == variant_id,
            )
        )
    if mapping is not None:
        return session.get(ProductModel, mapping.product_pk)
    if sku:
        mapping = session.scalar(
            select(ExternalProductMappingModel).where(
                ExternalProductMappingModel.store_id == row.store_id,
                ExternalProductMappingModel.provider_connection_id == row.id,
                ExternalProductMappingModel.external_sku == sku,
            )
        )
        if mapping is not None:
            return session.get(ProductModel, mapping.product_pk)
    return None


def _upsert_order(
    session: Session,
    row: ProviderConnectionModel,
    external: ExternalOrder,
) -> str:
    mapping = session.scalar(
        select(ExternalOrderMappingModel).where(
            ExternalOrderMappingModel.store_id == row.store_id,
            ExternalOrderMappingModel.provider_connection_id == row.id,
            ExternalOrderMappingModel.external_order_id == external.external_order_id,
        )
    )
    payload_hash = _hash_payload(external.raw)
    created = mapping is None
    if mapping is not None and mapping.payload_hash == payload_hash:
        return "unchanged"
    customer = _customer_for_order(session, row, external)
    order = session.get(OrderModel, mapping.order_id) if mapping else None
    previous_status = order.status if order else None
    status = _order_status(external.status)
    if order is None:
        order = OrderModel(
            store_id=row.store_id,
            customer_id=customer.id,
            status=status.value,
            payment_status=_payment_status_for_order(status),
            fulfillment_status=_fulfillment_status_for_order(status),
            currency=external.currency,
            subtotal_numeric=Decimal("0"),
            discount_numeric=Decimal("0"),
            total_numeric=Decimal("0"),
            shipping_json=external.shipping,
            provider_references_json={row.provider: external.external_order_id},
            notes=f"Imported from {row.provider}",
        )
        session.add(order)
        session.flush()
        mapping = ExternalOrderMappingModel(
            store_id=row.store_id,
            provider_connection_id=row.id,
            order_id=order.id,
            external_order_id=external.external_order_id,
            payload_hash=payload_hash,
        )
        session.add(mapping)
    else:
        assert mapping is not None
        session.execute(delete(OrderItemModel).where(OrderItemModel.order_id == order.id))
        order.customer_id = customer.id
        order.status = status.value
        order.payment_status = _payment_status_for_order(status)
        order.fulfillment_status = _fulfillment_status_for_order(status)
        order.currency = external.currency
        order.shipping_json = external.shipping
        order.updated_at = datetime.now(UTC)
        mapping.payload_hash = payload_hash
    subtotal = Decimal("0")
    for line in external.lines:
        product = _mapped_product(session, row, line.external_variant_id, line.sku)
        if product is None:
            continue
        line_total = line.unit_price * line.quantity
        subtotal += line_total
        variant = session.scalar(
            select(ProductVariantModel).where(
                ProductVariantModel.store_id == row.store_id,
                ProductVariantModel.product_pk == product.id,
                ProductVariantModel.sku == line.sku,
            )
        )
        session.add(
            OrderItemModel(
                order_id=order.id,
                product_pk=product.id,
                variant_pk=variant.id if variant is not None else None,
                product_id=product.product_id,
                variant_id=variant.variant_id if variant is not None else None,
                sku=line.sku or product.sku,
                options_json=dict(variant.options_json) if variant is not None else {},
                product_name=line.name,
                unit_price_numeric=line.unit_price,
                quantity=line.quantity,
                line_total_numeric=line_total,
            )
        )
    order.subtotal_numeric = subtotal
    order.total_numeric = subtotal
    if previous_status != status.value:
        session.add(
            OrderTransitionModel(
                order_id=order.id,
                from_status=previous_status,
                to_status=status.value,
                reason=f"{row.provider}_sync",
            )
        )
    mapping.source_updated_at = external.updated_at
    mapping.updated_at = datetime.now(UTC)
    session.flush()
    return "created" if created else "updated"


def sync_commerce_connection(
    session: Session,
    settings: Settings,
    store_id: str,
    connection_id: str,
) -> CommerceSyncResult:
    repository = ProviderConnectionRepository(session, store_id)
    row = repository.get(connection_id)
    if row.provider not in {"shopify", "woocommerce", "generic_website"}:
        raise InvalidInputError("Connection is not a commerce provider")
    credentials = repository.credentials(connection_id)
    connector = _connector(settings, row, credentials)
    try:
        products = connector.list_products()
        product_results = [_upsert_product(session, row, item) for item in products]
        seen_products = {(item.external_product_id, item.external_variant_id) for item in products}
        existing_mappings = session.scalars(
            select(ExternalProductMappingModel).where(
                ExternalProductMappingModel.store_id == store_id,
                ExternalProductMappingModel.provider_connection_id == row.id,
            )
        ).all()
        for mapping in existing_mappings:
            if (
                mapping.external_product_id,
                mapping.external_variant_id,
            ) not in seen_products:
                product = session.get(ProductModel, mapping.product_pk)
                if product is not None:
                    product.status = ProductStatus.DRAFT.value
                    product.stock = 0
                    product.updated_at = datetime.now(UTC)
        orders = connector.list_orders()
        order_results = [_upsert_order(session, row, item) for item in orders]
    except ExternalProviderError as exc:
        row.status = ProviderConnectionStatus.DEGRADED.value
        row.last_error_code = "sync_failed"
        row.last_error_message = str(exc)[:500]
        row.last_health_at = datetime.now(UTC)
        session.flush()
        raise
    now = datetime.now(UTC)
    row.status = ProviderConnectionStatus.CONNECTED.value
    row.last_successful_sync_at = now
    row.last_health_at = now
    row.last_error_code = None
    row.last_error_message = None
    session.flush()
    return CommerceSyncResult(
        connection_id=row.id,
        products_created=product_results.count("created"),
        products_updated=product_results.count("updated"),
        orders_created=order_results.count("created"),
        orders_updated=order_results.count("updated"),
        synced_at=now,
    )


def claim_commerce_webhook(
    session: Session,
    row: ProviderConnectionModel,
    external_event_id: str,
    event_type: str,
) -> bool:
    try:
        with session.begin_nested():
            session.add(
                ProviderWebhookEventModel(
                    store_id=row.store_id,
                    provider=row.provider,
                    external_account_id=row.external_account_id or row.external_resource_id,
                    external_event_id=external_event_id,
                    event_type=event_type,
                )
            )
            session.flush()
    except IntegrityError:
        return False
    enqueue_job(
        session,
        job_type="commerce.sync",
        store_id=row.store_id,
        payload={"store_id": row.store_id, "connection_id": row.id},
        dedup_key=f"commerce-webhook:{row.provider}:{external_event_id}",
    )
    return True


@job_handler("commerce.sync")
def commerce_sync_job(session: Session, payload: dict[str, object]) -> None:
    if _SETTINGS is None:
        raise RuntimeError("Commerce services are not configured")
    sync_commerce_connection(
        session,
        _SETTINGS,
        str(payload["store_id"]),
        str(payload["connection_id"]),
    )
