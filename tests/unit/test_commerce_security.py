from __future__ import annotations

import socket

import httpx
import pytest

from app.domain.errors import ExternalProviderError, InvalidInputError
from app.integrations.commerce import (
    GenericCommerceConnector,
    WooCommerceConnector,
    validate_public_https_url,
)
from app.integrations.commerce_modules import woocommerce as woocommerce_module


def test_commerce_url_rejects_private_and_non_https(monkeypatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))],
    )
    with pytest.raises(InvalidInputError):
        validate_public_https_url("https://internal.example")
    with pytest.raises(InvalidInputError):
        validate_public_https_url("http://store.example")


def test_shopify_url_is_restricted_to_myshopify(monkeypatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))],
    )
    assert (
        validate_public_https_url("https://merchant.myshopify.com/", shopify=True)
        == "https://merchant.myshopify.com"
    )
    with pytest.raises(InvalidInputError):
        validate_public_https_url("https://merchant.example", shopify=True)


def test_commerce_request_uses_pinned_ip_with_original_tls_identity(monkeypatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))],
    )
    calls: list[dict[str, object]] = []

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"status": "ok", "store_id": "store-1", "name": "Store"}

    def request(_client: httpx.Client, method: str, url: str, **kwargs: object) -> Response:
        calls.append({"method": method, "url": url, **kwargs})
        return Response()

    monkeypatch.setattr(httpx.Client, "request", request)
    connector = GenericCommerceConnector("https://store.example", "token", 5)
    assert connector.check_connection() == ("store-1", "Store")

    assert calls[0]["url"] == "https://8.8.8.8/commerce-ai/v1/health"
    assert calls[0]["headers"] == {
        "Authorization": "Bearer token",
        "Host": "store.example",
    }
    assert calls[0]["extensions"] == {"sni_hostname": "store.example"}


def test_woocommerce_pagination_has_a_hard_page_ceiling(monkeypatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))],
    )
    connector = WooCommerceConnector("https://store.example", "key", "secret", 5)
    monkeypatch.setattr(connector, "MAX_SYNC_PAGES", 2, raising=False)
    calls = 0

    def endless_pages(*args: object, **kwargs: object) -> list[dict[str, int]]:
        nonlocal calls
        calls += 1
        if calls > 2:
            raise AssertionError("provider pagination was not bounded")
        return [{"id": index} for index in range(100)]

    monkeypatch.setattr(connector, "_request", endless_pages)
    with pytest.raises(ExternalProviderError):
        connector._all("products")


def test_woocommerce_pagination_has_a_total_time_ceiling(monkeypatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))],
    )
    connector = WooCommerceConnector("https://store.example", "key", "secret", 5)
    monkeypatch.setattr(connector, "MAX_SYNC_SECONDS", 1.0)
    timestamps = iter([0.0, 2.0])
    monkeypatch.setattr(woocommerce_module.time, "monotonic", lambda: next(timestamps))
    monkeypatch.setattr(
        connector,
        "_request",
        lambda *args, **kwargs: pytest.fail("request started after the total deadline"),
    )

    with pytest.raises(ExternalProviderError):
        connector._all("products")
