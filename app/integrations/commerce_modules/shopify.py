"""Generated shopify slice of commerce.py."""

from __future__ import annotations

from typing import Any

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


class ShopifyConnector:
    def __init__(
        self,
        store_url: str,
        access_token: str,
        api_version: str,
        timeout_seconds: float,
    ):
        self._origin = _resolve_public_https_origin(store_url, shopify=True)
        self.store_url = self._origin.public_url
        self._token = access_token
        self._endpoint = f"admin/api/{api_version}/graphql.json"
        self._timeout = timeout_seconds

    def _graphql(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            response = _pinned_request(
                self._origin,
                "POST",
                self._endpoint,
                headers={
                    "X-Shopify-Access-Token": self._token,
                    "Content-Type": "application/json",
                },
                json={"query": query, "variables": variables or {}},
                timeout=self._timeout,
            )
            response.raise_for_status()
            body = response.json()
            if not isinstance(body, dict) or body.get("errors"):
                raise ValueError("Shopify returned GraphQL errors")
            data = body.get("data")
            if not isinstance(data, dict):
                raise ValueError("Shopify response has no data")
            return dict(data)
        except (httpx.HTTPError, ValueError) as exc:
            raise ExternalProviderError("Shopify request failed") from exc

    def check_connection(self) -> tuple[str, str]:
        shop = self._graphql("{ shop { id name myshopifyDomain } }").get("shop", {})
        if not isinstance(shop, dict) or not shop.get("id"):
            raise ExternalProviderError("Shopify shop identity is unavailable")
        return str(shop["id"]), str(shop.get("name") or shop.get("myshopifyDomain") or "Shopify")

    def list_products(self) -> list[ExternalProduct]:
        query = """
        query Products($cursor: String) {
          products(first: 50, after: $cursor) {
            pageInfo { hasNextPage endCursor }
            nodes {
              id title descriptionHtml productType status updatedAt
              featuredMedia { preview { image { url } } }
              variants(first: 100) {
                nodes {
                  id title sku price inventoryQuantity
                  inventoryItem { id }
                }
              }
            }
          }
        }
        """
        output: list[ExternalProduct] = []
        cursor: str | None = None
        while True:
            connection = self._graphql(query, {"cursor": cursor}).get("products", {})
            if not isinstance(connection, dict):
                break
            for product in connection.get("nodes", []):
                if not isinstance(product, dict):
                    continue
                product_id = str(product.get("id", "")).rsplit("/", 1)[-1]
                media = product.get("featuredMedia") or {}
                preview = media.get("preview") if isinstance(media, dict) else {}
                image = preview.get("image") if isinstance(preview, dict) else {}
                image_url = str(image.get("url", "")) if isinstance(image, dict) else ""
                variants = product.get("variants") or {}
                nodes = variants.get("nodes", []) if isinstance(variants, dict) else []
                for variant in nodes:
                    if not isinstance(variant, dict):
                        continue
                    variant_id = str(variant.get("id", "")).rsplit("/", 1)[-1]
                    title = str(product.get("title", ""))
                    variant_title = str(variant.get("title", ""))
                    name = (
                        title
                        if variant_title in {"", "Default Title"}
                        else f"{title} - {variant_title}"
                    )
                    inventory_item = variant.get("inventoryItem") or {}
                    output.append(
                        ExternalProduct(
                            external_product_id=product_id,
                            external_variant_id=variant_id,
                            external_inventory_id=(
                                str(inventory_item.get("id", "")).rsplit("/", 1)[-1]
                                if isinstance(inventory_item, dict)
                                else None
                            ),
                            sku=str(variant.get("sku") or variant_id),
                            name=name,
                            category=str(product.get("productType") or "Shopify"),
                            description=_text(product.get("descriptionHtml")),
                            price=_decimal(variant.get("price")),
                            stock=max(0, int(variant.get("inventoryQuantity") or 0)),
                            image_url=image_url,
                            active=str(product.get("status", "")).upper() == "ACTIVE",
                            updated_at=_timestamp(product.get("updatedAt")),
                            raw={"product": product, "variant": variant},
                        )
                    )
            page = connection.get("pageInfo") or {}
            if not isinstance(page, dict) or not page.get("hasNextPage"):
                break
            cursor = str(page.get("endCursor") or "")
            if not cursor:
                break
        return output

    def list_orders(self) -> list[ExternalOrder]:
        query = """
        query Orders($cursor: String) {
          orders(first: 50, after: $cursor, sortKey: UPDATED_AT) {
            pageInfo { hasNextPage endCursor }
            nodes {
              id name updatedAt displayFinancialStatus displayFulfillmentStatus currencyCode
              customer { id displayName email phone }
              shippingAddress { address1 address2 city province country zip }
              lineItems(first: 100) {
                nodes {
                  name quantity originalUnitPriceSet { shopMoney { amount } }
                  variant { id sku }
                }
              }
            }
          }
        }
        """
        output: list[ExternalOrder] = []
        cursor: str | None = None
        while True:
            connection = self._graphql(query, {"cursor": cursor}).get("orders", {})
            if not isinstance(connection, dict):
                break
            for order in connection.get("nodes", []):
                if not isinstance(order, dict):
                    continue
                customer = order.get("customer") or {}
                address = order.get("shippingAddress") or {}
                lines: list[ExternalOrderLine] = []
                line_connection = order.get("lineItems") or {}
                for line in (
                    line_connection.get("nodes", []) if isinstance(line_connection, dict) else []
                ):
                    if not isinstance(line, dict):
                        continue
                    variant = line.get("variant") or {}
                    money_set = line.get("originalUnitPriceSet") or {}
                    money = money_set.get("shopMoney") if isinstance(money_set, dict) else {}
                    lines.append(
                        ExternalOrderLine(
                            external_variant_id=(
                                str(variant.get("id", "")).rsplit("/", 1)[-1]
                                if isinstance(variant, dict)
                                else ""
                            ),
                            sku=str(variant.get("sku", "")) if isinstance(variant, dict) else "",
                            name=str(line.get("name", "Item")),
                            quantity=max(1, int(line.get("quantity") or 1)),
                            unit_price=_decimal(
                                money.get("amount") if isinstance(money, dict) else 0
                            ),
                        )
                    )
                financial = str(order.get("displayFinancialStatus") or "").lower()
                fulfillment = str(order.get("displayFulfillmentStatus") or "").lower()
                status = "paid" if financial in {"paid", "partially_refunded"} else "pending"
                if financial in {"refunded", "voided"}:
                    status = "refunded" if financial == "refunded" else "cancelled"
                elif fulfillment == "fulfilled":
                    status = "shipped"
                output.append(
                    ExternalOrder(
                        external_order_id=str(order.get("id", "")).rsplit("/", 1)[-1],
                        status=status,
                        currency=str(order.get("currencyCode") or "USD")[:3],
                        customer_external_id=(
                            str(customer.get("id", "")).rsplit("/", 1)[-1]
                            if isinstance(customer, dict)
                            else ""
                        ),
                        customer_name=(
                            str(customer.get("displayName") or "Shopify customer")
                            if isinstance(customer, dict)
                            else "Shopify customer"
                        ),
                        customer_email=(
                            str(customer.get("email") or "") if isinstance(customer, dict) else ""
                        ),
                        customer_phone=(
                            str(customer.get("phone") or "") if isinstance(customer, dict) else ""
                        ),
                        shipping={
                            key: str(address.get(key) or "")
                            for key in (
                                "address1",
                                "address2",
                                "city",
                                "province",
                                "country",
                                "zip",
                            )
                            if isinstance(address, dict) and address.get(key)
                        },
                        lines=lines,
                        updated_at=_timestamp(order.get("updatedAt")),
                        raw=order,
                    )
                )
            page = connection.get("pageInfo") or {}
            if not isinstance(page, dict) or not page.get("hasNextPage"):
                break
            cursor = str(page.get("endCursor") or "")
            if not cursor:
                break
        return output

    def install_webhooks(self, callback_url: str, secret: str) -> None:
        del secret
        mutation = """
        mutation Hook($topic: WebhookSubscriptionTopic!, $callback: URL!) {
          webhookSubscriptionCreate(
            topic: $topic
            webhookSubscription: {callbackUrl: $callback, format: JSON}
          ) {
            webhookSubscription { id }
            userErrors { field message }
          }
        }
        """
        for topic in (
            "PRODUCTS_CREATE",
            "PRODUCTS_UPDATE",
            "PRODUCTS_DELETE",
            "ORDERS_CREATE",
            "ORDERS_UPDATED",
            "ORDERS_CANCELLED",
        ):
            result = self._graphql(mutation, {"topic": topic, "callback": callback_url})
            payload = result.get("webhookSubscriptionCreate", {})
            if not isinstance(payload, dict) or payload.get("userErrors"):
                raise ExternalProviderError("Shopify webhook registration failed")
