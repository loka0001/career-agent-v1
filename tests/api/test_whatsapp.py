from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime, timedelta

from pydantic import SecretStr
from sqlalchemy import func, select

from app.db.models import (
    ChannelModel,
    ConversationModel,
    CustomerConsentModel,
    CustomerModel,
    MessageModel,
    ProviderConnectionModel,
)
from app.domain.enums import ChannelType
from app.integrations.whatsapp import WhatsAppCloudAdapter, WhatsAppManagementClient


def test_reading_whatsapp_settings_does_not_create_a_channel(context) -> None:
    registered = context.client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Settings Read Test",
            "store_name": "Empty Channel Store",
            "email": f"whatsapp-read-{uuid.uuid4().hex[:8]}@example.com",
            "password": "another-strong-pass-123",
            "full_name": "Settings Reader",
        },
    )
    assert registered.status_code == 201, registered.text
    store_id = registered.json()["user"]["store_id"]
    response = context.client.get("/api/v1/integrations/whatsapp")
    assert response.status_code == 200, response.text
    assert response.json()["channel_id"] is None
    assert response.json()["configured"] is False
    assert context.client.get("/api/v1/integrations/whatsapp/templates").json() == []
    check = context.client.post(
        "/api/v1/integrations/whatsapp/check",
        headers={"X-CSRF-Token": registered.json()["csrf_token"]},
    )
    assert check.status_code == 409
    with context.session_factory() as session:
        channels = session.scalars(
            select(ChannelModel).where(ChannelModel.store_id == store_id)
        ).all()
        assert channels == []
    context.login()


def _live_settings() -> dict[str, object]:
    return {
        "mode": "live",
        "display_name": "Demo WhatsApp",
        "phone_number_id": "phone-123456",
        "waba_id": "waba-987654",
        "access_token": "test-access-token",
        "app_secret": "test-app-secret",
        "verify_token": "test-verify-token",
        "is_active": True,
    }


def _webhook_payload(message_id: str = "wamid.inbound-1") -> dict[str, object]:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "waba-987654",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {"phone_number_id": "phone-123456"},
                            "contacts": [{"wa_id": "201001112233", "profile": {"name": "Mona"}}],
                            "messages": [
                                {
                                    "from": "201001112233",
                                    "id": message_id,
                                    "timestamp": "1700000000",
                                    "type": "text",
                                    "text": {"body": "عايزة سماعة للمكالمات"},
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }


def _signed_headers(raw: bytes) -> dict[str, str]:
    digest = hmac.new(b"test-app-secret", raw, hashlib.sha256).hexdigest()
    return {
        "Content-Type": "application/json",
        "X-Hub-Signature-256": f"sha256={digest}",
    }


def test_whatsapp_settings_are_encrypted_and_masked(authenticated) -> None:
    context, headers = authenticated
    response = context.client.put(
        "/api/v1/integrations/whatsapp", headers=headers, json=_live_settings()
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["configured"] is True
    assert body["masked_phone_number_id"].endswith("3456")
    assert "test-access-token" not in response.text

    with context.session_factory() as session:
        channel = session.scalar(
            select(ChannelModel).where(
                ChannelModel.store_id == "demo-store",
                ChannelModel.channel_type == ChannelType.WHATSAPP.value,
            )
        )
        assert channel is not None
        assert channel.provider_connection_id
        assert channel.credentials_json == {}
        connection = session.get(ProviderConnectionModel, channel.provider_connection_id)
        assert connection is not None
        stored = json.dumps(connection.credentials_json)
        assert set(connection.credentials_json) == {"ciphertext", "key_version"}
        assert connection.credentials_json["key_version"] == 1
        assert "test-access-token" not in stored


def test_whatsapp_webhook_verification_signature_and_idempotency(authenticated) -> None:
    context, headers = authenticated
    settings = context.client.put(
        "/api/v1/integrations/whatsapp", headers=headers, json=_live_settings()
    ).json()
    channel_id = settings["channel_id"]

    verify = context.client.get(
        f"/webhooks/whatsapp/{channel_id}",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "test-verify-token",
            "hub.challenge": "challenge-42",
        },
    )
    assert verify.status_code == 200
    assert verify.text == "challenge-42"

    raw = json.dumps(_webhook_payload(), separators=(",", ":")).encode()
    unsigned = context.client.post(
        f"/webhooks/whatsapp/{channel_id}",
        content=raw,
        headers={"Content-Type": "application/json"},
    )
    assert unsigned.status_code == 403

    first = context.client.post(
        f"/webhooks/whatsapp/{channel_id}", content=raw, headers=_signed_headers(raw)
    )
    second = context.client.post(
        f"/webhooks/whatsapp/{channel_id}", content=raw, headers=_signed_headers(raw)
    )
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    with context.session_factory() as session:
        stored = session.scalar(
            select(func.count(MessageModel.id)).where(MessageModel.external_id == "wamid.inbound-1")
        )
        assert stored == 1


def test_whatsapp_webhook_ignores_unexpected_phone_number_id(authenticated) -> None:
    context, headers = authenticated
    settings = context.client.put(
        "/api/v1/integrations/whatsapp", headers=headers, json=_live_settings()
    ).json()
    channel_id = settings["channel_id"]
    payload = _webhook_payload("wamid.wrong-phone")
    value = payload["entry"][0]["changes"][0]["value"]  # type: ignore[index]
    value["metadata"] = {"phone_number_id": "phone-other"}  # type: ignore[index]
    raw = json.dumps(payload, separators=(",", ":")).encode()

    response = context.client.post(
        f"/webhooks/whatsapp/{channel_id}", content=raw, headers=_signed_headers(raw)
    )

    assert response.status_code == 200, response.text
    assert response.json()["processed"] == 0
    with context.session_factory() as session:
        stored = session.scalar(
            select(func.count(MessageModel.id)).where(
                MessageModel.external_id == "wamid.wrong-phone"
            )
        )
        assert stored == 0


def test_whatsapp_service_window_templates_and_opt_out(authenticated) -> None:
    context, headers = authenticated
    settings = context.client.put(
        "/api/v1/integrations/whatsapp", headers=headers, json=_live_settings()
    ).json()
    channel_id = settings["channel_id"]
    raw = json.dumps(_webhook_payload("wamid.service-window"), separators=(",", ":")).encode()
    assert (
        context.client.post(
            f"/webhooks/whatsapp/{channel_id}", content=raw, headers=_signed_headers(raw)
        ).status_code
        == 200
    )

    with context.session_factory.begin() as session:
        conversation = session.scalar(
            select(ConversationModel)
            .join(ChannelModel, ConversationModel.channel_id == ChannelModel.id)
            .where(ChannelModel.id == channel_id)
            .order_by(ConversationModel.id.desc())
        )
        assert conversation is not None
        conversation.last_inbound_at = datetime.now(UTC) - timedelta(hours=25)
        conversation_id = conversation.id

    free_form = context.client.post(
        f"/api/v1/inbox/conversations/{conversation_id}/reply",
        headers={**headers, "Idempotency-Key": f"reply-{uuid.uuid4().hex}"},
        json={"text": "متابعة"},
    )
    assert free_form.status_code == 409
    assert free_form.json()["error"]["details"]["reason"] == "service_window_closed"

    demo_payload = _live_settings()
    demo_payload["mode"] = "demo"
    demo_payload["access_token"] = ""
    demo_payload["app_secret"] = ""
    demo_payload["verify_token"] = ""
    context.client.put("/api/v1/integrations/whatsapp", headers=headers, json=demo_payload)
    template = context.client.post(
        "/api/v1/integrations/whatsapp/templates",
        headers=headers,
        json={
            "name": "follow_up",
            "language": "ar",
            "body": "أهلًا {{name}}، هل ما زلت مهتمًا؟",
            "variables": ["name"],
        },
    )
    assert template.status_code == 201, template.text
    with context.session_factory.begin() as session:
        conversation = session.get(ConversationModel, conversation_id)
        assert conversation is not None
        customer = conversation.customer_id
        customer_row = session.get(CustomerModel, customer)
        assert customer_row is not None
        customer_row.consent_json = {"whatsapp": True}
    sent = context.client.post(
        f"/api/v1/integrations/whatsapp/conversations/{conversation_id}/template",
        headers=headers,
        json={"template_id": template.json()["id"], "variables": {"name": "منى"}},
    )
    assert sent.status_code == 202, sent.text
    assert sent.json()["status"] == "queued"
    assert context.container.job_queue.run_due_jobs() >= 1
    delivered = context.client.get(
        f"/api/v1/inbox/conversations/{conversation_id}", headers=headers
    )
    assert delivered.status_code == 200
    assert delivered.json()["messages"][-1]["status"] == "sent"


def test_embedded_signup_and_live_template_reconciliation(context, monkeypatch) -> None:
    registered = context.client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "WhatsApp Embedded Organization",
            "store_name": "WhatsApp Embedded Store",
            "email": f"wa-embedded-{uuid.uuid4().hex[:8]}@example.com",
            "password": "Embedded-Secure-Password-2026!",
            "full_name": "Embedded Owner",
        },
    )
    assert registered.status_code == 201, registered.text
    headers = {"X-CSRF-Token": registered.json()["csrf_token"]}
    settings = context.container.settings
    previous = (
        settings.meta_app_id,
        settings.meta_app_secret,
        settings.meta_whatsapp_config_id,
    )
    settings.meta_app_id = "app-123"
    settings.meta_app_secret = SecretStr("app-secret-123")
    settings.meta_whatsapp_config_id = "config-123"
    calls: list[str] = []
    monkeypatch.setattr(
        WhatsAppManagementClient,
        "exchange_code",
        lambda self, code, app_id, app_secret: "embedded-access-token",
    )
    monkeypatch.setattr(
        WhatsAppManagementClient,
        "discover_waba_ids",
        lambda self, token, app_id, app_secret: ["waba-embedded"],
    )
    monkeypatch.setattr(
        WhatsAppManagementClient,
        "list_phone_numbers",
        lambda self, token, waba_id: [
            {
                "phone_number_id": "phone-embedded",
                "waba_id": waba_id,
                "display_phone_number": "+201000000000",
                "verified_name": "Embedded Store",
                "quality_rating": "GREEN",
                "verification_status": "VERIFIED",
            }
        ],
    )
    monkeypatch.setattr(
        WhatsAppManagementClient,
        "subscribe_app",
        lambda self, token, waba_id: calls.append(f"subscribe:{waba_id}"),
    )
    monkeypatch.setattr(
        WhatsAppManagementClient,
        "register_phone",
        lambda self, token, phone_id, pin: calls.append(f"register:{phone_id}"),
    )
    monkeypatch.setattr(
        WhatsAppCloudAdapter,
        "check_connection",
        lambda self, credentials: (True, None),
    )
    monkeypatch.setattr(
        WhatsAppManagementClient,
        "create_template",
        lambda self, token, waba_id, payload: {
            "id": "template-meta-1",
            "status": "PENDING",
        },
    )
    monkeypatch.setattr(
        WhatsAppManagementClient,
        "list_templates",
        lambda self, token, waba_id: [
            {
                "id": "template-meta-1",
                "name": "order_update",
                "language": "ar",
                "status": "APPROVED",
                "category": "UTILITY",
                "components": [{"type": "BODY", "text": "مرحبًا {{1}}، تم تحديث طلبك."}],
                "quality_score": {"score": "GREEN"},
            }
        ],
    )
    try:
        started = context.client.post(
            "/api/v1/integrations/whatsapp/embedded/start",
            headers=headers,
        )
        assert started.status_code == 200, started.text
        exchange = context.client.post(
            "/api/v1/integrations/whatsapp/embedded/exchange",
            headers=headers,
            json={"code": "embedded-code", "state": started.json()["state"]},
        )
        assert exchange.status_code == 200, exchange.text
        assert "embedded-access-token" not in exchange.text
        phone = exchange.json()["phones"][0]
        connected = context.client.post(
            "/api/v1/integrations/whatsapp/embedded/connect",
            headers=headers,
            json={
                "transaction_id": exchange.json()["transaction_id"],
                "phone_number_id": phone["phone_number_id"],
                "waba_id": phone["waba_id"],
            },
        )
        assert connected.status_code == 200, connected.text
        assert connected.json()["connection_status"] == "connected"
        assert calls == ["subscribe:waba-embedded", "register:phone-embedded"]

        created = context.client.post(
            "/api/v1/integrations/whatsapp/templates",
            headers=headers,
            json={
                "name": "order_update",
                "language": "ar",
                "body": "مرحبًا {{name}}، تم تحديث طلبك.",
                "variables": ["name"],
                "category": "UTILITY",
            },
        )
        assert created.status_code == 201, created.text
        assert created.json()["status"] == "pending"
        synced = context.client.post(
            "/api/v1/integrations/whatsapp/templates/sync",
            headers=headers,
        )
        assert synced.status_code == 200, synced.text
        assert synced.json()[0]["status"] == "approved"
        assert synced.json()[0]["quality_score"] == "GREEN"
    finally:
        (
            settings.meta_app_id,
            settings.meta_app_secret,
            settings.meta_whatsapp_config_id,
        ) = previous
        context.login()


def test_whatsapp_media_and_consent_audit(authenticated, monkeypatch) -> None:
    context, headers = authenticated
    settings = context.client.put(
        "/api/v1/integrations/whatsapp", headers=headers, json=_live_settings()
    ).json()
    channel_id = settings["channel_id"]
    monkeypatch.setattr(
        WhatsAppManagementClient,
        "download_media",
        lambda self, token, media_id, max_bytes: (
            b"%PDF-1.4 test",
            "application/pdf",
        ),
    )
    payload = _webhook_payload("wamid.document")
    value = payload["entry"][0]["changes"][0]["value"]  # type: ignore[index]
    value["messages"][0] = {  # type: ignore[index]
        "from": "201001112233",
        "id": "wamid.document",
        "timestamp": "1700000001",
        "type": "document",
        "document": {
            "id": "media-document-1",
            "mime_type": "application/pdf",
            "filename": "invoice.pdf",
        },
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    received = context.client.post(
        f"/webhooks/whatsapp/{channel_id}",
        content=raw,
        headers=_signed_headers(raw),
    )
    assert received.status_code == 200, received.text
    with context.session_factory() as session:
        message = session.scalar(
            select(MessageModel).where(MessageModel.external_id == "wamid.document")
        )
        assert message is not None
        assert message.attachments_json[0]["type"] == "document"
        assert message.attachments_json[0]["url"].startswith("http://testserver/")
        conversation_id = message.conversation_id

    media = context.client.post(
        f"/api/v1/integrations/whatsapp/conversations/{conversation_id}/media",
        headers=headers,
        data={"caption": "الفاتورة المحدثة"},
        files={"media": ("invoice.pdf", b"%PDF-1.4 outbound", "application/pdf")},
    )
    assert media.status_code == 202, media.text
    assert media.json()["attachments"][0]["type"] == "document"

    opt_out_payload = _webhook_payload("wamid.opt-out")
    opt_out_value = opt_out_payload["entry"][0]["changes"][0]["value"]  # type: ignore[index]
    opt_out_value["messages"][0]["text"]["body"] = "STOP"  # type: ignore[index]
    raw_opt_out = json.dumps(opt_out_payload, separators=(",", ":")).encode()
    opted_out = context.client.post(
        f"/webhooks/whatsapp/{channel_id}",
        content=raw_opt_out,
        headers=_signed_headers(raw_opt_out),
    )
    assert opted_out.status_code == 200
    with context.session_factory() as session:
        consent = session.scalar(
            select(CustomerConsentModel)
            .where(CustomerConsentModel.store_id == "demo-store")
            .order_by(CustomerConsentModel.id.desc())
        )
        assert consent is not None
        assert consent.status == "opted_out"
        assert consent.source == "inbound_keyword"
