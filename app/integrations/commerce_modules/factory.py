"""Generated factory slice of commerce.py."""

from __future__ import annotations

import base64

from app.domain.errors import AuthenticationError, InvalidInputError
from app.integrations.commerce_modules.common import CommerceConnector
from app.integrations.commerce_modules.generic import GenericCommerceConnector
from app.integrations.commerce_modules.shopify import ShopifyConnector
from app.integrations.commerce_modules.woocommerce import WooCommerceConnector


def connector_for(
    provider: str,
    credentials: dict[str, str],
    *,
    shopify_api_version: str,
    timeout_seconds: float,
) -> CommerceConnector:
    if provider == "shopify":
        return ShopifyConnector(
            credentials.get("store_url", ""),
            credentials.get("access_token", ""),
            shopify_api_version,
            timeout_seconds,
        )
    if provider == "woocommerce":
        return WooCommerceConnector(
            credentials.get("store_url", ""),
            credentials.get("consumer_key", ""),
            credentials.get("consumer_secret", ""),
            timeout_seconds,
        )
    if provider == "generic_website":
        return GenericCommerceConnector(
            credentials.get("store_url", ""),
            credentials.get("access_token", ""),
            timeout_seconds,
        )
    raise InvalidInputError("Unsupported commerce provider")


def verify_commerce_signature(
    provider: str,
    body: bytes,
    signature: str | None,
    secret: str,
) -> None:
    import hashlib
    import hmac

    if not signature or not secret:
        raise AuthenticationError("Commerce webhook signature is missing")
    digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode()
    if provider == "generic_website":
        expected = "sha256=" + digest.hex()
    if not hmac.compare_digest(signature, expected):
        raise AuthenticationError("Commerce webhook signature is invalid")
