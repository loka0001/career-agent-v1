"""Generated generic slice of commerce.py."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

import httpx

from app.domain.errors import ExternalProviderError
from app.integrations.commerce_modules.common import (
    ExternalOrder,
    ExternalOrderLine,
    ExternalProduct,
    _decimal,
    _pinned_request,
    _resolve_public_https_origin,
    _text,
    _timestamp,
)


class GenericCommerceConnector:
    def __init__(
        self,
        store_url: str,
        access_token: str,
        timeout_seconds: float,
    ):
        self._origin = _resolve_public_https_origin(store_url)
        self.store_url = self._origin.public_url
        self._token = access_token
        self._base = "commerce-ai/v1"
        self._timeout = timeout_seconds

    def _request(self, method: str, path: str, *, json_body: dict[str, Any] | None = None) -> Any:
        try:
            response = _pinned_request(
                self._origin,
                method,
                f"{self._base}/{path.lstrip('/')}",
                headers={"Authorization": f"Bearer {self._token}"},
                json=json_body,
                timeout=self._timeout,
            )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ExternalProviderError("Generic commerce connector request failed") from exc

    def check_connection(self) -> tuple[str, str]:
        result = self._request("GET", "health")
        if not isinstance(result, dict) or result.get("status") != "ok":
            raise ExternalProviderError("Generic commerce health check failed")
        return str(result.get("store_id") or self.store_url), str(
            result.get("name") or urlsplit(self.store_url).hostname or "Website"
        )

    def list_products(self) -> list[ExternalProduct]:
        payload = self._request("GET", "products")
        rows = payload.get("data", payload) if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            raise ExternalProviderError("Generic products response is invalid")
        output: list[ExternalProduct] = []
        for item in rows:
            if not isinstance(item, dict):
                continue
            variants = item.get("variants") or [item]
            for variant in variants:
                if not isinstance(variant, dict):
                    continue
                output.append(
                    ExternalProduct(
                        external_product_id=str(item.get("id", "")),
                        external_variant_id=str(variant.get("id", "")),
                        external_inventory_id=str(variant.get("inventory_id") or "") or None,
                        sku=str(variant.get("sku") or variant.get("id") or item.get("id")),
                        name=str(item.get("name") or "Website product"),
                        category=str(item.get("category") or "Website"),
                        description=_text(item.get("description")),
                        price=_decimal(variant.get("price") or item.get("price")),
                        stock=max(0, int(variant.get("stock") or item.get("stock") or 0)),
                        image_url=str(item.get("image_url") or ""),
                        active=bool(item.get("active", True)),
                        updated_at=_timestamp(item.get("updated_at")),
                        raw={"product": item, "variant": variant},
                    )
                )
        return output

    def list_orders(self) -> list[ExternalOrder]:
        payload = self._request("GET", "orders")
        rows = payload.get("data", payload) if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            raise ExternalProviderError("Generic orders response is invalid")
        output: list[ExternalOrder] = []
        for item in rows:
            if not isinstance(item, dict):
                continue
            customer = item.get("customer") or {}
            output.append(
                ExternalOrder(
                    external_order_id=str(item.get("id", "")),
                    status=str(item.get("status") or "pending"),
                    currency=str(item.get("currency") or "USD")[:3],
                    customer_external_id=str(customer.get("id") or ""),
                    customer_name=str(customer.get("name") or "Website customer"),
                    customer_email=str(customer.get("email") or ""),
                    customer_phone=str(customer.get("phone") or ""),
                    shipping={
                        str(key): str(value)
                        for key, value in dict(item.get("shipping") or {}).items()
                    },
                    lines=[
                        ExternalOrderLine(
                            external_variant_id=str(line.get("variant_id") or ""),
                            sku=str(line.get("sku") or ""),
                            name=str(line.get("name") or "Item"),
                            quantity=max(1, int(line.get("quantity") or 1)),
                            unit_price=_decimal(line.get("unit_price")),
                        )
                        for line in item.get("lines", [])
                        if isinstance(line, dict)
                    ],
                    updated_at=_timestamp(item.get("updated_at")),
                    raw=item,
                )
            )
        return output

    def install_webhooks(self, callback_url: str, secret: str) -> None:
        result = self._request(
            "POST",
            "webhooks",
            json_body={
                "url": callback_url,
                "secret": secret,
                "events": ["product.*", "order.*"],
            },
        )
        if not isinstance(result, dict) or not result.get("id"):
            raise ExternalProviderError("Generic webhook registration failed")
