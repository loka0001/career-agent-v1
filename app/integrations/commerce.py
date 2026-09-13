"""Compatibility exports for the split commerce modules."""

from __future__ import annotations

from app.integrations.commerce_modules.common import (
    CommerceConnector,
    ExternalOrder,
    ExternalOrderLine,
    ExternalProduct,
    PinnedHTTPSOrigin,
    _decimal,
    _pinned_request,
    _resolve_public_https_origin,
    _text,
    _timestamp,
    validate_public_https_url,
)
from app.integrations.commerce_modules.factory import connector_for, verify_commerce_signature
from app.integrations.commerce_modules.generic import GenericCommerceConnector
from app.integrations.commerce_modules.shopify import ShopifyConnector
from app.integrations.commerce_modules.woocommerce import WooCommerceConnector

__all__ = [
    "CommerceConnector",
    "ExternalOrder",
    "ExternalOrderLine",
    "ExternalProduct",
    "GenericCommerceConnector",
    "PinnedHTTPSOrigin",
    "ShopifyConnector",
    "WooCommerceConnector",
    "_decimal",
    "_pinned_request",
    "_resolve_public_https_origin",
    "_text",
    "_timestamp",
    "connector_for",
    "validate_public_https_url",
    "verify_commerce_signature",
]
