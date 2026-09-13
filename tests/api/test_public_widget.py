"""Website integration kit: API keys, public chat, events, catalog, rate limits."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, tzinfo

import pytest

from tests.conftest import TestContext

SITE_ORIGIN = "https://shop.example"


def _create_key(context: TestContext, headers: dict[str, str]) -> str:
    response = context.client.post(
        "/api/v1/api-keys",
        headers=headers,
        json={
            "name": f"site-{uuid.uuid4().hex[:6]}",
            "allowed_origins": [SITE_ORIGIN],
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["key"].startswith("pk_")
    assert body["api_key"]["key_prefix"] == body["key"][:11]
    assert body["api_key"]["allowed_origins"] == [SITE_ORIGIN]
    return str(body["key"])


def test_api_key_lifecycle(authenticated: tuple[TestContext, dict[str, str]]) -> None:
    context, headers = authenticated
    key = _create_key(context, headers)
    listing = context.client.get("/api/v1/api-keys")
    assert listing.status_code == 200
    rows = listing.json()
    assert all("key" not in row or row.get("key") is None for row in rows)  # plaintext never listed
    target = next(row for row in rows if row["key_prefix"] == key[:11])
    revoke = context.client.post(f"/api/v1/api-keys/{target['id']}/revoke", headers=headers)
    assert revoke.status_code == 200
    assert revoke.json()["is_active"] is False
    denied = context.client.post(
        "/api/v1/public/events",
        headers={"X-Api-Key": key, "Origin": SITE_ORIGIN},
        json={"session_key": "sess-12345678", "event_type": "page_view"},
    )
    assert denied.status_code == 401


def test_public_chat_grounded_and_captured_in_inbox(
    authenticated: tuple[TestContext, dict[str, str]],
) -> None:
    context, headers = authenticated
    key = _create_key(context, headers)
    session_key = f"sess{uuid.uuid4().hex[:12]}"
    chat = context.client.post(
        "/api/v1/public/chat",
        headers={"X-Api-Key": key, "Origin": SITE_ORIGIN},
        json={
            "session_key": session_key,
            "message": "عايز سماعة للمذاكرة وميزانيتي 1500 جنيه",
            "customer_name": "زائر تجريبي",
        },
    )
    assert chat.status_code == 200, chat.text
    payload = chat.json()
    assert payload["reply"]
    assert 1 <= len(payload["recommendations"]) <= 3
    assert all(float(r["product"]["price"]) <= 1500 for r in payload["recommendations"])

    detail = context.client.get(f"/api/v1/inbox/conversations/{payload['conversation_id']}")
    assert detail.status_code == 200
    senders = [m["sender_type"] for m in detail.json()["messages"]]
    assert "customer" in senders and "assistant" in senders


def test_public_chat_has_independent_per_client_limit(
    authenticated: tuple[TestContext, dict[str, str]],
) -> None:
    context, headers = authenticated
    key = _create_key(context, headers)
    request_headers = {
        "X-Api-Key": key,
        "Origin": SITE_ORIGIN,
        "X-Client-Fingerprint": "client-fixed-12345678",
    }

    for index in range(12):
        response = context.client.post(
            "/api/v1/public/chat",
            headers=request_headers,
            json={
                "session_key": "sess-client-limit",
                "message": f"Recommend a product {index}",
            },
        )
        assert response.status_code == 200, response.text

    blocked = context.client.post(
        "/api/v1/public/chat",
        headers=request_headers,
        json={"session_key": "sess-client-limit", "message": "One more"},
    )
    assert blocked.status_code == 429


def test_events_tracking_respects_consent(
    authenticated: tuple[TestContext, dict[str, str]],
) -> None:
    context, headers = authenticated
    key = _create_key(context, headers)
    batch = context.client.post(
        "/api/v1/public/events",
        headers={"X-Api-Key": key, "Origin": SITE_ORIGIN},
        json={
            "events": [
                {
                    "session_key": "sess-abcd1234",
                    "event_type": "page_view",
                    "payload": {"path": "/"},
                    "consented": True,
                },
                {
                    "session_key": "sess-abcd1234",
                    "event_type": "product_view",
                    "product_id": "A101",
                    "consented": True,
                },
                {
                    "session_key": "sess-abcd1234",
                    "event_type": "search",
                    "consented": False,
                },
            ]
        },
    )
    assert batch.status_code == 202
    assert batch.json()["accepted"] == 2  # non-consented search dropped

    invalid = context.client.post(
        "/api/v1/public/events",
        headers={"X-Api-Key": key, "Origin": SITE_ORIGIN},
        json={"session_key": "sess-abcd1234", "event_type": "not_a_real_event"},
    )
    assert invalid.status_code == 422


def test_catalog_requires_valid_key(authenticated: tuple[TestContext, dict[str, str]]) -> None:
    context, headers = authenticated
    key = _create_key(context, headers)
    catalog = context.client.get(
        "/api/v1/public/catalog",
        headers={"X-Api-Key": key, "Origin": SITE_ORIGIN},
    )
    assert catalog.status_code == 200
    items = catalog.json()
    assert len(items) >= 24
    assert all(item["stock"] >= 0 and float(item["price"]) > 0 for item in items)
    bogus = context.client.get(
        "/api/v1/public/catalog",
        headers={"X-Api-Key": "pk_wrong", "Origin": SITE_ORIGIN},
    )
    assert bogus.status_code == 401
    missing = context.client.get("/api/v1/public/catalog")
    assert missing.status_code == 401


def test_widget_preflight_and_origin_allowlist(
    authenticated: tuple[TestContext, dict[str, str]],
) -> None:
    context, headers = authenticated
    key = _create_key(context, headers)
    allowed = context.client.options(
        f"/api/v1/public/events?key={key}",
        headers={
            "Origin": SITE_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-api-key",
        },
    )
    assert allowed.status_code == 204
    assert allowed.headers["access-control-allow-origin"] == SITE_ORIGIN

    blocked = context.client.options(
        f"/api/v1/public/events?key={key}",
        headers={
            "Origin": "https://attacker.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert blocked.status_code == 403

    stolen = context.client.post(
        "/api/v1/public/events",
        headers={"X-Api-Key": key, "Origin": "https://attacker.example"},
        json={"session_key": "sess-denied123", "event_type": "page_view"},
    )
    assert stolen.status_code == 401


def test_public_events_rate_limit_returns_http_429(
    authenticated: tuple[TestContext, dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz: tzinfo | None = None) -> datetime:
            return datetime(2026, 9, 2, 0, 0, 30, tzinfo=tz or UTC)

    monkeypatch.setattr("app.services.rate_limits.datetime", FixedDateTime)
    context, headers = authenticated
    key = _create_key(context, headers)
    event = {"session_key": "sess-ratelimit", "event_type": "page_view", "consented": False}
    request_headers = {"X-Api-Key": key, "Origin": SITE_ORIGIN}

    for _ in range(240):
        accepted = context.client.post(
            "/api/v1/public/events",
            headers=request_headers,
            json=event,
        )
        assert accepted.status_code == 202, accepted.text

    blocked = context.client.post(
        "/api/v1/public/events",
        headers=request_headers,
        json=event,
    )
    assert blocked.status_code == 429, blocked.text
    assert blocked.json()["error"]["code"] == "rate_limited"
    assert blocked.json()["error"]["details"]["retry_after_seconds"] >= 1
