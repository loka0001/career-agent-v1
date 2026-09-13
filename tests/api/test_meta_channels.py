from __future__ import annotations

import hashlib
import hmac
import json

from sqlalchemy import func, select

from app.db.models import (
    ChannelModel,
    MessageModel,
    OAuthTransactionModel,
    ProviderConnectionModel,
)
from app.domain.enums import ChannelType


def _signature(raw: bytes) -> str:
    return "sha256=" + hmac.new(b"demo-meta-app-secret", raw, hashlib.sha256).hexdigest()


def test_demo_meta_oauth_connects_channels_without_exposing_token(authenticated) -> None:
    context, headers = authenticated
    started = context.client.post("/api/v1/integrations/meta/channels/oauth/start", headers=headers)
    assert started.status_code == 200, started.text
    assert started.json()["demo"] is True
    exchanged = context.client.post(
        "/api/v1/integrations/meta/channels/oauth/exchange",
        headers=headers,
        json={"code": "demo", "state": started.json()["state"]},
    )
    assert exchanged.status_code == 200, exchanged.text
    assert "demo-token" not in exchanged.text
    account = exchanged.json()["accounts"][0]
    transaction_id = exchanged.json()["transaction_id"]
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
    assert len(connected.json()) == 4
    assert all(item["configured"] for item in connected.json())
    with context.session_factory() as session:
        rows = session.scalars(
            select(ChannelModel).where(
                ChannelModel.store_id == "demo-store",
                ChannelModel.channel_type.in_(
                    (
                        ChannelType.MESSENGER.value,
                        ChannelType.INSTAGRAM_DM.value,
                        ChannelType.FACEBOOK_COMMENTS.value,
                        ChannelType.INSTAGRAM_COMMENTS.value,
                    )
                ),
            )
        ).all()
        assert len(rows) == 4
        assert all(not row.credentials_json for row in rows)
        assert all(row.provider_connection_id for row in rows)
        connection_ids = {row.provider_connection_id for row in rows}
        connections = session.scalars(
            select(ProviderConnectionModel).where(ProviderConnectionModel.id.in_(connection_ids))
        ).all()
        assert len(connections) == 2
        assert all(
            set(row.credentials_json) == {"ciphertext", "key_version"} for row in connections
        )
        assert "demo-token" not in json.dumps([row.credentials_json for row in connections])
        transaction = session.get(OAuthTransactionModel, transaction_id)
        assert transaction is not None
        assert transaction.completed_at is not None
        assert transaction.result_credentials_json == {}


def test_signed_meta_message_webhook_is_idempotent(authenticated) -> None:
    context, headers = authenticated
    channels = context.client.get("/api/v1/integrations/meta/channels", headers=headers).json()
    messenger = next(item for item in channels if item["channel_type"] == "messenger")
    channel_id = messenger["channel_id"]
    verify = context.client.get(
        f"/webhooks/meta/{channel_id}",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": hashlib.sha256(
                b"demo-store:demo-page:test-secret-key-with-enough-entropy"
            ).hexdigest()[:32],
            "hub.challenge": "meta-ok",
        },
    )
    assert verify.status_code == 200
    assert verify.text == "meta-ok"
    payload = {
        "object": "page",
        "entry": [
            {
                "id": "demo-page",
                "messaging": [
                    {
                        "sender": {"id": "meta-customer-1"},
                        "recipient": {"id": "demo-page"},
                        "message": {"mid": "mid.demo.1", "text": "عايز أعرف السعر"},
                    }
                ],
            }
        ],
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    unsigned = context.client.post(
        f"/webhooks/meta/{channel_id}",
        content=raw,
        headers={"Content-Type": "application/json"},
    )
    assert unsigned.status_code == 401
    for _ in range(2):
        response = context.client.post(
            f"/webhooks/meta/{channel_id}",
            content=raw,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": _signature(raw),
            },
        )
        assert response.status_code == 200, response.text
    with context.session_factory() as session:
        count = session.scalar(
            select(func.count(MessageModel.id)).where(MessageModel.external_id == "mid.demo.1")
        )
        assert count == 1
