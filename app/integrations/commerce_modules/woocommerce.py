"""Generated woocommerce slice of commerce.py."""

from __future__ import annotations

import time
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


class WooCommerceConnector:
    MAX_SYNC_PAGES = 100
    MAX_SYNC_SECONDS = 300.0

    def __init__(
        self,
        store_url: str,
        consumer_key: str,
        consumer_secret: str,
        timeout_seconds: float,
    ):
        self._origin = _resolve_public_https_origin(store_url)
        self.store_url = self._origin.public_url
        self._auth = (consumer_key, consumer_secret)
        self._base = "wp-json/wc/v3"
        self._timeout = timeout_seconds

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        try:
            response = _pinned_request(
                self._origin,
                method,
                f"{self._base}/{path.lstrip('/')}",
                auth=self._auth,
                params=params,
                json=json_body,
                timeout=self._timeout,
            )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ExternalProviderError("WooCommerce request failed") from exc

    def check_connection(self) -> tuple[str, str]:
        products = self._request("GET", "products", params={"per_page": 1})
        if not isinstance(products, list):
            raise ExternalProviderError("WooCommerce product API is unavailable")
        return self.store_url, urlsplit(self.store_url).hostname or "WooCommerce"

    def _all(self, resource: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        deadline = time.monotonic() + self.MAX_SYNC_SECONDS
        for page in range(1, self.MAX_SYNC_PAGES + 1):
            if time.monotonic() >= deadline:
                raise ExternalProviderError("WooCommerce pagination exceeded the time limit")
            payload = self._request("GET", resource, params={"per_page": 100, "page": page})
            if not isinstance(payload, list):
                return rows
            rows.extend(item for item in payload if isinstance(item, dict))
            if len(payload) < 100:
                return rows
        raise ExternalProviderError("WooCommerce pagination exceeded the page limit")

    def list_products(self) -> list[ExternalProduct]:
        output: list[ExternalProduct] = []
        for product in self._all("products"):
            product_id = str(product.get("id", ""))
            variants: list[dict[str, Any]]
            if product.get("type") == "variable":
                variants = self._all(f"products/{product_id}/variations")
            else:
                variants = [product]
            images = product.get("images") or []
            image_url = (
                str(images[0].get("src", "")) if images and isinstance(images[0], dict) else ""
            )
            for variant in variants:
                variant_id = str(variant.get("id", "")) if variant is not product else ""
                variant_name = " / ".join(
                    str(item.get("option", ""))
                    for item in variant.get("attributes", [])
                    if isinstance(item, dict) and item.get("option")
                )
                name = str(product.get("name") or "WooCommerce product")
                if variant_name:
                    name = f"{name} - {variant_name}"
                output.append(
                    ExternalProduct(
                        external_product_id=product_id,
                        external_variant_id=variant_id,
                        external_inventory_id=None,
                        sku=str(variant.get("sku") or variant_id or product_id),
                        name=name,
                        category=(
                            str(product["categories"][0].get("name", "WooCommerce"))
                            if product.get("categories")
                            and isinstance(product["categories"][0], dict)
                            else "WooCommerce"
                        ),
                        description=_text(
                            product.get("short_description") or product.get("description")
                        ),
                        price=_decimal(variant.get("price") or product.get("price")),
                        stock=max(
                            0,
                            int(
                                variant.get("stock_quantity") or product.get("stock_quantity") or 0
                            ),
                        ),
                        image_url=image_url,
                        active=product.get("status") == "publish",
                        updated_at=_timestamp(product.get("date_modified_gmt")),
                        raw={"product": product, "variant": variant},
                    )
                )
        return output

    def list_orders(self) -> list[ExternalOrder]:
        output: list[ExternalOrder] = []
        for order in self._all("orders"):
            billing = order.get("billing") or {}
            shipping = order.get("shipping") or {}
            lines = [
                ExternalOrderLine(
                    external_variant_id=str(line.get("variation_id") or ""),
                    sku=str(line.get("sku") or ""),
                    name=str(line.get("name") or "Item"),
                    quantity=max(1, int(line.get("quantity") or 1)),
                    unit_price=(
                        _decimal(line.get("subtotal")) / max(1, int(line.get("quantity") or 1))
                    ),
                )
                for line in order.get("line_items", [])
                if isinstance(line, dict)
            ]
            status_map = {
                "pending": "pending",
                "processing": "processing",
                "on-hold": "confirmed",
                "completed": "delivered",
                "cancelled": "cancelled",
                "refunded": "refunded",
                "failed": "cancelled",
            }
            output.append(
                ExternalOrder(
                    external_order_id=str(order.get("id", "")),
                    status=status_map.get(str(order.get("status")), "pending"),
                    currency=str(order.get("currency") or "USD")[:3],
                    customer_external_id=str(order.get("customer_id") or ""),
                    customer_name=" ".join(
                        filter(
                            None,
                            (
                                str(billing.get("first_name") or ""),
                                str(billing.get("last_name") or ""),
                            ),
                        )
                    )
                    or "WooCommerce customer",
                    customer_email=str(billing.get("email") or ""),
                    customer_phone=str(billing.get("phone") or ""),
                    shipping={
                        key: str(shipping.get(key) or "")
                        for key in (
                            "address_1",
                            "address_2",
                            "city",
                            "state",
                            "country",
                            "postcode",
                        )
                        if shipping.get(key)
                    },
                    lines=lines,
                    updated_at=_timestamp(order.get("date_modified_gmt")),
                    raw=order,
                )
            )
        return output

    def install_webhooks(self, callback_url: str, secret: str) -> None:
        for topic in (
            "product.created",
            "product.updated",
            "product.deleted",
            "order.created",
            "order.updated",
            "order.deleted",
        ):
            result = self._request(
                "POST",
                "webhooks",
                json_body={
                    "name": f"Commerce AI {topic}",
                    "topic": topic,
                    "delivery_url": callback_url,
                    "secret": secret,
                    "status": "active",
                },
            )
            if not isinstance(result, dict) or not result.get("id"):
                raise ExternalProviderError("WooCommerce webhook registration failed")
