"""Commerce connector contract, sync idempotency, signatures, and tenancy."""

from __future__ import annotations

import base64
import hashlib
import hmac
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from urllib.parse import parse_qs, urlencode, urlparse

from pydantic import SecretStr
from sqlalchemy import select

from app.db.models import OAuthTransactionModel, ProviderConnectionModel
from app.integrations.commerce import ExternalOrder, ExternalOrderLine, ExternalProduct
from app.services import commerce_connectors


class FakeCommerceConnector:
    store_url = "https://store.example"

    def __init__(self) -> None:
        self.webhooks: list[tuple[str, str]] = []

    def check_connection(self) -> tuple[str, str]:
        return "external-store-1", "External Store"

    def install_webhooks(self, callback_url: str, secret: str) -> None:
        self.webhooks.append((callback_url, secret))

    def list_products(self) -> list[ExternalProduct]:
        now = datetime.now(UTC)
        return [
            ExternalProduct(
                external_product_id="product-1",
                external_variant_id=variant,
                external_inventory_id=f"inventory-{variant}",
                sku=sku,
                name=f"Imported Product {sku}",
                category="Imported",
                description="Imported from the contract fixture.",
                price=price,
                stock=stock,
                image_url="https://cdn.example/product.jpg",
                active=True,
                updated_at=now,
                raw={"id": "product-1", "variant": variant, "stock": stock},
            )
            for variant, sku, price, stock in (
                ("variant-1", "SKU-RED", Decimal("120.00"), 5),
                ("variant-2", "SKU-BLUE", Decimal("135.00"), 7),
            )
        ]

    def list_orders(self) -> list[ExternalOrder]:
        return [
            ExternalOrder(
                external_order_id="order-1",
                status="paid",
                currency="EGP",
                customer_external_id="customer-1",
                customer_name="Imported Customer",
                customer_email="imported@example.com",
                customer_phone="+201000000000",
                shipping={"city": "Cairo"},
                lines=[
                    ExternalOrderLine(
                        external_variant_id="variant-1",
                        sku="SKU-RED",
                        name="Imported Product Red",
                        quantity=2,
                        unit_price=Decimal("120.00"),
                    )
                ],
                updated_at=datetime.now(UTC),
                raw={"id": "order-1", "status": "paid", "version": 1},
            )
        ]


class FakeShopifyTokenResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, str]:
        return {
            "access_token": "oauth-shopify-token",
            "scope": "read_products,read_orders,write_webhooks",
        }


def _shopify_hmac(secret: str, params: dict[str, str]) -> str:
    return hmac.new(
        secret.encode(),
        urlencode(sorted(params.items())).encode(),
        hashlib.sha256,
    ).hexdigest()


def test_shopify_oauth_install_lifecycle_is_signed_secret_safe_and_single_use(
    authenticated, monkeypatch
) -> None:
    owner_context, headers = authenticated
    fake = FakeCommerceConnector()
    monkeypatch.setattr(owner_context.container.settings, "shopify_app_api_key", "shopify-app-key")
    monkeypatch.setattr(
        owner_context.container.settings,
        "shopify_app_api_secret",
        SecretStr("shopify-app-secret"),
    )
    monkeypatch.setattr(
        owner_context.container.settings,
        "shopify_oauth_redirect_uri",
        "https://commerce.example.com/shopify/oauth/callback",
    )
    monkeypatch.setattr(
        commerce_connectors,
        "connector_for",
        lambda provider, credentials, **kwargs: (
            setattr(fake, "store_url", credentials["store_url"]) or fake
        ),
    )

    token_requests: list[dict[str, object]] = []

    def fake_post(url: str, **kwargs: object) -> FakeShopifyTokenResponse:
        token_requests.append({"url": url, **kwargs})
        return FakeShopifyTokenResponse()

    monkeypatch.setattr(commerce_connectors.httpx, "post", fake_post)
    started = owner_context.client.post(
        "/api/v1/integrations/commerce/shopify/oauth/start",
        headers=headers,
        json={
            "display_name": "OAuth Shopify",
            "shop": "merchant.myshopify.com",
            "install_webhooks": True,
        },
    )
    assert started.status_code == 200, started.text
    start_body = started.json()
    assert start_body["shop"] == "merchant.myshopify.com"
    auth_query = parse_qs(urlparse(start_body["authorization_url"]).query)
    assert auth_query["client_id"] == ["shopify-app-key"]
    assert auth_query["state"] == [start_body["state"]]
    assert auth_query["redirect_uri"] == ["https://commerce.example.com/shopify/oauth/callback"]

    callback_params = {
        "code": "temporary-code",
        "shop": "merchant.myshopify.com",
        "state": start_body["state"],
        "timestamp": "1780000000",
    }
    signed_callback_params = {**callback_params, "host": "encoded-host"}
    callback_hmac = _shopify_hmac("shopify-app-secret", signed_callback_params)
    callback = owner_context.client.get(
        "/shopify/oauth/callback",
        params={**signed_callback_params, "hmac": callback_hmac},
        follow_redirects=False,
    )
    assert callback.status_code == 307
    redirect = urlparse(callback.headers["location"])
    assert redirect.path == "/app/integrations"
    redirect_query = parse_qs(redirect.query)
    assert redirect_query["shopify_code"] == ["temporary-code"]
    assert redirect_query["shopify_state"] == [start_body["state"]]
    assert redirect_query["shopify_shop"] == ["merchant.myshopify.com"]
    assert redirect_query["shopify_hmac"] == [callback_hmac]
    assert redirect_query["shopify_timestamp"] == ["1780000000"]
    assert redirect_query["shopify_host"] == ["encoded-host"]

    exchanged = owner_context.client.post(
        "/api/v1/integrations/commerce/shopify/oauth/exchange",
        headers=headers,
        json={
            **callback_params,
            "hmac": callback_hmac,
            "host": "encoded-host",
        },
    )
    assert exchanged.status_code == 200, exchanged.text
    body = exchanged.json()
    assert body["provider"] == "shopify"
    assert body["status"] == "connected"
    assert body["external_resource_id"] == "https://merchant.myshopify.com"
    assert body["scopes"] == ["read_orders", "read_products", "write_webhooks"]
    assert "oauth-shopify-token" not in exchanged.text
    assert token_requests == [
        {
            "url": "https://merchant.myshopify.com/admin/oauth/access_token",
            "json": {
                "client_id": "shopify-app-key",
                "client_secret": "shopify-app-secret",
                "code": "temporary-code",
            },
            "timeout": owner_context.container.settings.commerce_request_timeout_seconds,
        }
    ]
    assert fake.webhooks == [
        (
            f"http://testserver/webhooks/commerce/{body['id']}",
            "shopify-app-secret",
        )
    ]
    assert "shopify-app-secret" not in exchanged.text

    webhook_payload = b'{"id":"oauth-product-1","updated_at":"2026-08-01T09:00:00Z"}'
    webhook_signature = base64.b64encode(
        hmac.new(b"shopify-app-secret", webhook_payload, hashlib.sha256).digest()
    ).decode()
    invalid_webhook = owner_context.client.post(
        f"/webhooks/commerce/{body['id']}",
        headers={
            "X-Shopify-Hmac-Sha256": "wrong-signature",
            "X-Shopify-Webhook-Id": "oauth-delivery-invalid",
            "X-Shopify-Topic": "products/update",
            "Content-Type": "application/json",
        },
        content=webhook_payload,
    )
    accepted_webhook = owner_context.client.post(
        f"/webhooks/commerce/{body['id']}",
        headers={
            "X-Shopify-Hmac-Sha256": webhook_signature,
            "X-Shopify-Webhook-Id": "oauth-delivery-valid",
            "X-Shopify-Topic": "products/update",
            "Content-Type": "application/json",
        },
        content=webhook_payload,
    )
    assert invalid_webhook.status_code == 401
    assert accepted_webhook.status_code == 202
    assert accepted_webhook.json()["enqueued"] is True

    replay = owner_context.client.post(
        "/api/v1/integrations/commerce/shopify/oauth/exchange",
        headers=headers,
        json={
            **callback_params,
            "hmac": callback_hmac,
            "host": "encoded-host",
        },
    )
    assert replay.status_code == 401

    with owner_context.session_factory.begin() as session:
        transaction = session.scalar(
            select(OAuthTransactionModel).where(OAuthTransactionModel.provider == "shopify")
        )
        assert transaction is not None
        assert transaction.completed_at is not None
        assert transaction.result_credentials_json == {}
        connection = session.get(ProviderConnectionModel, body["id"])
        assert connection is not None
        assert connection.metadata_json["oauth_installation"] is True
        assert connection.metadata_json["webhook_secret_source"] == "shopify_app_api_secret"


def test_shopify_oauth_rejects_invalid_hmac_without_consuming_state(
    authenticated, monkeypatch
) -> None:
    owner_context, headers = authenticated
    fake = FakeCommerceConnector()
    monkeypatch.setattr(owner_context.container.settings, "shopify_app_api_key", "shopify-app-key")
    monkeypatch.setattr(
        owner_context.container.settings,
        "shopify_app_api_secret",
        SecretStr("shopify-app-secret"),
    )
    monkeypatch.setattr(
        owner_context.container.settings,
        "shopify_oauth_redirect_uri",
        "https://commerce.example.com/shopify/oauth/callback",
    )
    monkeypatch.setattr(
        commerce_connectors,
        "connector_for",
        lambda provider, credentials, **kwargs: (
            setattr(fake, "store_url", credentials["store_url"]) or fake
        ),
    )
    token_calls = 0

    def fake_post(url: str, **kwargs: object) -> FakeShopifyTokenResponse:
        nonlocal token_calls
        token_calls += 1
        return FakeShopifyTokenResponse()

    monkeypatch.setattr(commerce_connectors.httpx, "post", fake_post)
    started = owner_context.client.post(
        "/api/v1/integrations/commerce/shopify/oauth/start",
        headers=headers,
        json={
            "display_name": "OAuth Shopify",
            "shop": "merchant.myshopify.com",
            "install_webhooks": False,
        },
    )
    assert started.status_code == 200, started.text
    callback_params = {
        "code": "temporary-code",
        "shop": "merchant.myshopify.com",
        "state": started.json()["state"],
        "timestamp": "1780000000",
    }
    invalid_callback = owner_context.client.get(
        "/shopify/oauth/callback",
        params={**callback_params, "hmac": "0" * 64},
        follow_redirects=False,
    )
    assert invalid_callback.status_code == 401
    assert token_calls == 0

    rejected = owner_context.client.post(
        "/api/v1/integrations/commerce/shopify/oauth/exchange",
        headers=headers,
        json={**callback_params, "hmac": "0" * 64},
    )
    assert rejected.status_code == 401
    assert token_calls == 0

    accepted = owner_context.client.post(
        "/api/v1/integrations/commerce/shopify/oauth/exchange",
        headers=headers,
        json={
            **callback_params,
            "hmac": _shopify_hmac("shopify-app-secret", callback_params),
        },
    )
    assert accepted.status_code == 200, accepted.text
    assert token_calls == 1
    assert fake.webhooks == []


def test_commerce_connect_sync_webhook_and_tenant_isolation(
    authenticated, context, monkeypatch
) -> None:
    owner_context, headers = authenticated
    fake = FakeCommerceConnector()
    monkeypatch.setattr(
        commerce_connectors,
        "connector_for",
        lambda *args, **kwargs: fake,
    )
    secret = "commerce-webhook-secret-2026"
    connected = owner_context.client.post(
        "/api/v1/integrations/commerce",
        headers=headers,
        json={
            "provider": "generic_website",
            "display_name": "Contract Store",
            "store_url": "https://store.example",
            "access_token": "generic-access-token",
            "webhook_secret": secret,
            "install_webhooks": True,
        },
    )
    assert connected.status_code == 201, connected.text
    body = connected.json()
    assert body["status"] == "connected"
    assert body["external_account_id"] == "external-store-1"
    assert "generic-access-token" not in connected.text
    assert secret not in connected.text
    integration_status = owner_context.client.get("/api/v1/integrations", headers=headers)
    assert integration_status.status_code == 200, integration_status.text
    statuses = {item["name"]: item for item in integration_status.json()["integrations"]}
    assert statuses["commerce_connectors"]["configured"] is True
    assert statuses["commerce_connectors"]["mode"] == "connected"
    connected_count, total_count = (
        int(value)
        for value in statuses["commerce_connectors"]["masked_identifier"]
        .replace(" connected", "")
        .split("/")
    )
    assert connected_count >= 1
    assert total_count >= connected_count
    assert "generic-access-token" not in integration_status.text
    assert secret not in integration_status.text
    connection_id = body["id"]
    assert fake.webhooks == [
        (
            f"http://testserver/webhooks/commerce/{connection_id}",
            secret,
        )
    ]

    first = owner_context.client.post(
        f"/api/v1/integrations/commerce/{connection_id}/sync",
        headers=headers,
    )
    assert first.status_code == 200, first.text
    assert first.json()["products_created"] == 2
    assert first.json()["orders_created"] == 1

    second = owner_context.client.post(
        f"/api/v1/integrations/commerce/{connection_id}/sync",
        headers=headers,
    )
    assert second.status_code == 200, second.text
    assert second.json()["products_created"] == 0
    assert second.json()["products_updated"] == 0
    assert second.json()["orders_created"] == 0
    assert second.json()["orders_updated"] == 0

    products = owner_context.client.get("/api/v1/products")
    imported = [item for item in products.json() if item["category"] == "Imported"]
    assert len(imported) == 2
    orders = owner_context.client.get("/api/v1/orders")
    imported_orders = [
        item for item in orders.json() if item["notes"] == "Imported from generic_website"
    ]
    assert len(imported_orders) == 1
    assert imported_orders[0]["total"] == "240.00"

    payload = b'{"id":"product-1","updated_at":"2026-07-28T12:00:00Z"}'
    signature = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    webhook_headers = {
        "X-Commerce-Signature": signature,
        "X-Commerce-Event-ID": "delivery-1",
        "X-Commerce-Topic": "product.updated",
        "Content-Type": "application/json",
    }
    accepted = owner_context.client.post(
        f"/webhooks/commerce/{connection_id}",
        headers=webhook_headers,
        content=payload,
    )
    replay = owner_context.client.post(
        f"/webhooks/commerce/{connection_id}",
        headers=webhook_headers,
        content=payload,
    )
    assert accepted.status_code == 202
    assert accepted.json()["enqueued"] is True
    assert replay.status_code == 202
    assert replay.json()["enqueued"] is False

    other = context.client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Other Commerce Org",
            "store_name": "Other Commerce Store",
            "email": f"commerce-{uuid.uuid4().hex[:8]}@example.com",
            "password": "Other-Commerce-Secure-2026!",
            "full_name": "Other Owner",
        },
    )
    assert other.status_code == 201
    denied = context.client.post(
        f"/api/v1/integrations/commerce/{connection_id}/sync",
        headers={"X-CSRF-Token": other.json()["csrf_token"]},
    )
    assert denied.status_code == 404
