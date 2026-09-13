"""Generated common slice of commerce.py."""

from __future__ import annotations

import ipaddress
import re
import socket
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol
from urllib.parse import urlsplit

import httpx

from app.domain.errors import InvalidInputError


def _text(value: Any, *, limit: int = 4000) -> str:
    return re.sub(r"<[^>]+>", " ", str(value or "")).strip()[:limit]


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value or "0")).quantize(Decimal("0.01"))
    except InvalidOperation:
        return Decimal("0")


def _timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed


@dataclass(frozen=True)
class PinnedHTTPSOrigin:
    public_url: str
    connect_url: str
    host_header: str
    server_hostname: str


def _resolve_public_https_origin(value: str, *, shopify: bool = False) -> PinnedHTTPSOrigin:
    normalized = value.strip().rstrip("/")
    parsed = urlsplit(normalized)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise InvalidInputError("Store URL must be a clean HTTPS URL")
    if parsed.path not in {"", "/"}:
        raise InvalidInputError("Store URL cannot contain a path")
    hostname = parsed.hostname.casefold().rstrip(".")
    if shopify and not hostname.endswith(".myshopify.com"):
        raise InvalidInputError("Shopify URL must use the myshopify.com domain")
    try:
        addresses = {
            item[4][0]
            for item in socket.getaddrinfo(hostname, parsed.port or 443, type=socket.SOCK_STREAM)
        }
    except socket.gaierror as exc:
        raise InvalidInputError("Store hostname could not be resolved") from exc
    if not addresses:
        raise InvalidInputError("Store hostname could not be resolved")
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise InvalidInputError("Private or local store addresses are not allowed")
    port = f":{parsed.port}" if parsed.port else ""
    pinned_ip = min((ipaddress.ip_address(address) for address in addresses), key=str)
    connect_host = f"[{pinned_ip}]" if pinned_ip.version == 6 else str(pinned_ip)
    connect_port = f":{parsed.port}" if parsed.port else ""
    return PinnedHTTPSOrigin(
        public_url=f"https://{hostname}{port}",
        connect_url=f"https://{connect_host}{connect_port}",
        host_header=f"{hostname}{port}",
        server_hostname=hostname,
    )


def validate_public_https_url(value: str, *, shopify: bool = False) -> str:
    return _resolve_public_https_origin(value, shopify=shopify).public_url


def _pinned_request(
    origin: PinnedHTTPSOrigin,
    method: str,
    path: str,
    *,
    timeout: float,
    headers: dict[str, str] | None = None,
    **kwargs: Any,
) -> httpx.Response:
    request_headers = {"Host": origin.host_header, **(headers or {})}
    with httpx.Client(follow_redirects=False, trust_env=False) as client:
        return client.request(
            method,
            f"{origin.connect_url}/{path.lstrip('/')}",
            headers=request_headers,
            timeout=timeout,
            extensions={"sni_hostname": origin.server_hostname},
            **kwargs,
        )


@dataclass(frozen=True)
class ExternalProduct:
    external_product_id: str
    external_variant_id: str
    external_inventory_id: str | None
    sku: str
    name: str
    category: str
    description: str
    price: Decimal
    stock: int
    image_url: str
    active: bool
    updated_at: datetime | None
    raw: dict[str, Any]


@dataclass(frozen=True)
class ExternalOrderLine:
    external_variant_id: str
    sku: str
    name: str
    quantity: int
    unit_price: Decimal


@dataclass(frozen=True)
class ExternalOrder:
    external_order_id: str
    status: str
    currency: str
    customer_external_id: str
    customer_name: str
    customer_email: str
    customer_phone: str
    shipping: dict[str, str]
    lines: list[ExternalOrderLine]
    updated_at: datetime | None
    raw: dict[str, Any]


class CommerceConnector(Protocol):
    def check_connection(self) -> tuple[str, str]: ...

    def list_products(self) -> list[ExternalProduct]: ...

    def list_orders(self) -> list[ExternalOrder]: ...

    def install_webhooks(self, callback_url: str, secret: str) -> None: ...
