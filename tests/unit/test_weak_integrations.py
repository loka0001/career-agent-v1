from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from app.config import Settings
from app.domain.enums import ChannelType, Platform
from app.domain.errors import ConflictError, InvalidInputError
from app.integrations.billing import StripeBillingProvider
from app.integrations.chroma_store import ChromaStore
from app.integrations.malware_scanner import ClamAVMalwareScanner
from app.integrations.meta_channels import MetaChannelAdapter
from app.integrations.whatsapp import WhatsAppCloudAdapter
from app.services.meta_publishing import StoreMetaPublisher


def response(status: int, body: dict[str, Any]) -> httpx.Response:
    return httpx.Response(status, json=body, request=httpx.Request("POST", "https://provider.test"))


def test_chroma_normalizes_and_reranks_provider_results() -> None:
    normalized = ChromaStore._normalize_results(
        {
            "metadatas": [[{"product_id": "p1"}, {"product_id": "p2"}]],
            "documents": [["red running shoes", "formal black shoes"]],
            "distances": [[0.4, 0.1]],
        },
        "product_id",
    )
    ranked = ChromaStore._rerank(normalized, "red running", 1)
    assert ranked[0]["product_id"] == "p1"
    assert ranked[0]["lexical_score"] > 0


def test_meta_publishing_maps_provider_failure_without_leaking_message(monkeypatch) -> None:
    monkeypatch.setattr(
        httpx,
        "request",
        lambda *args, **kwargs: response(403, {"error": {"code": 190, "message": "secret"}}),
    )
    publisher = StoreMetaPublisher(None, Settings(), "store-1", Platform.FACEBOOK)  # type: ignore[arg-type]
    with pytest.raises(ConflictError) as caught:
        publisher._request("GET", "page-1", token="token")
    assert caught.value.details == {"platform": "facebook", "provider_code": "190"}
    assert "secret" not in str(caught.value)


def test_meta_channel_provider_returns_external_message_id(monkeypatch) -> None:
    monkeypatch.setattr(
        httpx,
        "post",
        lambda *args, **kwargs: response(200, {"message_id": "meta-message-1"}),
    )
    adapter = MetaChannelAdapter(ChannelType.MESSENGER, "https://graph.test", "v1", 2)
    result = adapter.send_text(
        {"access_token": "token", "account_id": "page-1"}, "customer-1", "Hello"
    )
    assert result.success is True
    assert result.external_id == "meta-message-1"


class FakeClamConnection:
    def __init__(self, reply: bytes):
        self.reply = reply
        self.sent: list[bytes] = []

    def __enter__(self) -> FakeClamConnection:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def settimeout(self, value: float) -> None:
        assert value == 2

    def sendall(self, value: bytes) -> None:
        self.sent.append(value)

    def recv(self, size: int) -> bytes:
        assert size == 4096
        return self.reply


def test_malware_scanner_rejects_detected_payload(monkeypatch) -> None:
    connection = FakeClamConnection(b"stream: Eicar-Test-Signature FOUND\0")
    monkeypatch.setattr("socket.create_connection", lambda *args, **kwargs: connection)
    with pytest.raises(InvalidInputError):
        ClamAVMalwareScanner("clamav", 3310, 2).scan(b"payload")
    assert connection.sent[0] == b"zINSTREAM\0"
    assert connection.sent[-1] == b"\0\0\0\0"


def test_whatsapp_provider_sends_bearer_authenticated_text(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def post(*args: object, **kwargs: Any) -> httpx.Response:
        captured.update(kwargs)
        return response(200, {"messages": [{"id": "wamid-1"}]})

    monkeypatch.setattr(httpx, "post", post)
    adapter = WhatsAppCloudAdapter("https://graph.test", "v1", 2)
    result = adapter.send_text(
        {"access_token": "token", "phone_number_id": "phone-1"}, "20100", "Hello"
    )
    assert result.external_id == "wamid-1"
    assert captured["headers"] == {"Authorization": "Bearer token"}


class FakeStripeApi:
    def post(
        self,
        path: str,
        data: list[tuple[str, str]],
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, object]:
        assert path == "/checkout/sessions"
        assert ("customer_email", "buyer@example.com") in data
        assert idempotency_key == "billing:org-1:pro"
        return {
            "url": "https://checkout.stripe.test/session",
            "expires_at": int(datetime(2030, 1, 1, tzinfo=UTC).timestamp()),
        }


def test_billing_provider_builds_idempotent_checkout() -> None:
    provider = StripeBillingProvider(FakeStripeApi(), {"pro": "price_1"})  # type: ignore[arg-type]
    checkout = provider.create_checkout(
        "org-1", "pro", None, "buyer@example.com", "https://commerce.test/"
    )
    assert checkout.url == "https://checkout.stripe.test/session"
    assert checkout.expires_at.year == 2030
