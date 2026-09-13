"""Provider connection security, OAuth lifecycle, and tenant isolation tests."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.db.models import OAuthTransactionModel
from tests.conftest import TestContext


def _start_and_exchange(
    context: TestContext, headers: dict[str, str]
) -> tuple[str, str, dict[str, object]]:
    started = context.client.post("/api/v1/integrations/meta/channels/oauth/start", headers=headers)
    assert started.status_code == 200, started.text
    state = str(started.json()["state"])
    exchanged = context.client.post(
        "/api/v1/integrations/meta/channels/oauth/exchange",
        headers=headers,
        json={"code": "demo", "state": state},
    )
    assert exchanged.status_code == 200, exchanged.text
    return state, str(exchanged.json()["transaction_id"]), dict(exchanged.json()["accounts"][0])


def _register_rival(context: TestContext) -> dict[str, str]:
    response = context.client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Connection Isolation",
            "store_name": "Rival Connection Store",
            "email": f"connections-{uuid.uuid4().hex[:10]}@example.com",
            "password": "another-strong-pass-123",
            "full_name": "Rival Owner",
        },
    )
    assert response.status_code == 201, response.text
    return {"X-CSRF-Token": str(response.json()["csrf_token"])}


def test_oauth_state_and_result_are_single_use(authenticated) -> None:
    context, headers = authenticated
    state, transaction_id, account = _start_and_exchange(context, headers)

    replay = context.client.post(
        "/api/v1/integrations/meta/channels/oauth/exchange",
        headers=headers,
        json={"code": "demo", "state": state},
    )
    assert replay.status_code == 401

    payload = {
        "transaction_id": transaction_id,
        "page_id": account["page_id"],
        "instagram_account_id": account["instagram_account_id"],
    }
    connected = context.client.post(
        "/api/v1/integrations/meta/channels/oauth/connect",
        headers=headers,
        json=payload,
    )
    assert connected.status_code == 200, connected.text
    repeated_connect = context.client.post(
        "/api/v1/integrations/meta/channels/oauth/connect",
        headers=headers,
        json=payload,
    )
    assert repeated_connect.status_code == 409

    listed = context.client.get("/api/v1/integrations/connections", headers=headers)
    assert listed.status_code == 200, listed.text
    meta_types = {item["connection_type"] for item in listed.json() if item["provider"] == "meta"}
    assert {"facebook_page", "instagram_business"} <= meta_types
    assert "credentials" not in listed.text
    assert "ciphertext" not in listed.text
    assert "demo-token" not in listed.text
    integration_status = context.client.get("/api/v1/integrations", headers=headers)
    assert integration_status.status_code == 200, integration_status.text
    statuses = {item["name"]: item for item in integration_status.json()["integrations"]}
    assert statuses["meta_social_connections"]["configured"] is True
    assert statuses["meta_social_connections"]["mode"] == "connected"
    assert statuses["meta_social_connections"]["masked_identifier"] == "2/2 connected"
    assert "demo-token" not in integration_status.text


def test_meta_check_uses_store_oauth_connections_without_global_credentials(
    authenticated, monkeypatch
) -> None:
    context, headers = authenticated
    _, transaction_id, account = _start_and_exchange(context, headers)
    connected = context.client.post(
        "/api/v1/integrations/meta/channels/oauth/connect",
        headers=headers,
        json={
            "transaction_id": transaction_id,
            "page_id": account["page_id"],
            "instagram_account_id": account["instagram_account_id"],
        },
    )
    assert connected.status_code == 200, connected.text

    def unexpected_global_check() -> bool:
        raise AssertionError("per-store Meta checks must not use global publisher credentials")

    monkeypatch.setattr(
        context.container.facebook_publisher, "check_connection", unexpected_global_check
    )
    monkeypatch.setattr(
        context.container.instagram_publisher,
        "check_connection",
        unexpected_global_check,
    )
    checked = context.client.post("/api/v1/integrations/meta/check", headers=headers)
    assert checked.status_code == 200, checked.text
    statuses = {item["name"]: item for item in checked.json()["integrations"]}
    assert statuses["meta_social_connections"]["configured"] is True
    assert statuses["meta_social_connections"]["mode"] == "connected"
    assert statuses["meta_social_connections"]["masked_identifier"] == "2/2 connected"
    assert "demo-token" not in checked.text


def test_oauth_state_expires_and_is_bound_to_user_and_store(authenticated) -> None:
    context, demo_headers = authenticated
    started = context.client.post(
        "/api/v1/integrations/meta/channels/oauth/start", headers=demo_headers
    )
    assert started.status_code == 200
    state = str(started.json()["state"])

    rival_headers = _register_rival(context)
    mismatched = context.client.post(
        "/api/v1/integrations/meta/channels/oauth/exchange",
        headers=rival_headers,
        json={"code": "demo", "state": state},
    )
    assert mismatched.status_code == 401

    demo_headers = context.login()
    opaque_state = state.split(".", 1)[0]
    with context.session_factory.begin() as session:
        transaction = session.scalar(
            select(OAuthTransactionModel).where(
                OAuthTransactionModel.state_hash
                == hashlib.sha256(opaque_state.encode("utf-8")).hexdigest()
            )
        )
        assert transaction is not None
        transaction.expires_at = datetime.now(UTC) - timedelta(seconds=1)

    expired = context.client.post(
        "/api/v1/integrations/meta/channels/oauth/exchange",
        headers=demo_headers,
        json={"code": "demo", "state": state},
    )
    assert expired.status_code == 401


def test_provider_connections_are_tenant_scoped(authenticated) -> None:
    context, demo_headers = authenticated
    _, transaction_id, account = _start_and_exchange(context, demo_headers)
    connected = context.client.post(
        "/api/v1/integrations/meta/channels/oauth/connect",
        headers=demo_headers,
        json={
            "transaction_id": transaction_id,
            "page_id": account["page_id"],
            "instagram_account_id": account["instagram_account_id"],
        },
    )
    assert connected.status_code == 200, connected.text
    demo_connections = context.client.get("/api/v1/integrations/connections")
    assert demo_connections.status_code == 200
    connection_id = str(demo_connections.json()[0]["id"])

    rival_headers = _register_rival(context)
    rival_connections = context.client.get("/api/v1/integrations/connections")
    assert rival_connections.status_code == 200
    assert rival_connections.json() == []
    forbidden = context.client.post(
        f"/api/v1/integrations/connections/{connection_id}/disconnect",
        headers=rival_headers,
    )
    assert forbidden.status_code == 404
    context.login()


def test_disconnecting_shared_meta_token_updates_all_linked_connections(
    authenticated,
) -> None:
    context, headers = authenticated
    _, transaction_id, account = _start_and_exchange(context, headers)
    connected = context.client.post(
        "/api/v1/integrations/meta/channels/oauth/connect",
        headers=headers,
        json={
            "transaction_id": transaction_id,
            "page_id": account["page_id"],
            "instagram_account_id": account["instagram_account_id"],
        },
    )
    assert connected.status_code == 200, connected.text
    current = context.client.get("/api/v1/integrations/connections").json()
    facebook = next(item for item in current if item["connection_type"] == "facebook_page")
    disconnected = context.client.post(
        f"/api/v1/integrations/connections/{facebook['id']}/disconnect",
        headers=headers,
    )
    assert disconnected.status_code == 200, disconnected.text
    after = context.client.get("/api/v1/integrations/connections").json()
    oauth_connections = [
        item for item in after if item["connection_type"] in {"facebook_page", "instagram_business"}
    ]
    assert {item["status"] for item in oauth_connections} == {"disconnected"}

    _, restore_transaction, restore_account = _start_and_exchange(context, headers)
    restored = context.client.post(
        "/api/v1/integrations/meta/channels/oauth/connect",
        headers=headers,
        json={
            "transaction_id": restore_transaction,
            "page_id": restore_account["page_id"],
            "instagram_account_id": restore_account["instagram_account_id"],
        },
    )
    assert restored.status_code == 200, restored.text
