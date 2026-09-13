"""Unified inbox: simulate, list, detail, suggest, reply via job queue, manage."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.db.models import AuditEventModel, ExternalOperationModel
from app.domain.models import SendResult
from app.services.external_operations import OUTCOME_UNKNOWN, begin_external_operation
from tests.conftest import TestContext


def _simulate(context: TestContext, headers: dict[str, str], text: str) -> dict[str, object]:
    response = context.client.post(
        "/api/v1/inbox/simulate",
        headers=headers,
        json={
            "text": text,
            "customer_name": "عميل اختبار",
            "external_id": f"t-{uuid.uuid4().hex[:8]}",
        },
    )
    assert response.status_code == 201, response.text
    return dict(response.json())


def test_inbound_message_creates_conversation(
    authenticated: tuple[TestContext, dict[str, str]],
) -> None:
    context, headers = authenticated
    detail = _simulate(context, headers, "عايز سماعة للمذاكرة وميزانيتي 1500 جنيه")
    assert detail["channel_type"] == "webchat"
    assert detail["status"] == "open"
    assert detail["unread_count"] == 1
    messages = detail["messages"]
    assert isinstance(messages, list) and len(messages) == 1

    listing = context.client.get("/api/v1/inbox/conversations")
    assert listing.status_code == 200
    ids = [item["id"] for item in listing.json()["conversations"]]
    assert detail["id"] in ids

    # Reading the detail marks it read.
    read = context.client.get(f"/api/v1/inbox/conversations/{detail['id']}")
    assert read.status_code == 200
    assert read.json()["unread_count"] == 0


def test_suggest_returns_grounded_recommendations(
    authenticated: tuple[TestContext, dict[str, str]],
) -> None:
    context, headers = authenticated
    detail = _simulate(context, headers, "عايز سماعة للمذاكرة والمكالمات وميزانيتي 1500 جنيه")
    suggestion = context.client.post(
        f"/api/v1/inbox/conversations/{detail['id']}/suggest", headers=headers
    )
    assert suggestion.status_code == 200, suggestion.text
    payload = suggestion.json()
    assert payload["need"]["intent"] == "product_search"
    assert 1 <= len(payload["recommendations"]) <= 3
    assert all(float(r["product"]["price"]) <= 1500 for r in payload["recommendations"])
    assert payload["reply"]


def test_reply_is_queued_then_sent_by_job(
    authenticated: tuple[TestContext, dict[str, str]],
) -> None:
    context, headers = authenticated
    detail = _simulate(context, headers, "هل الشحن متاح للإسكندرية؟")
    reply_headers = {
        **headers,
        "Idempotency-Key": f"reply-{uuid.uuid4().hex}",
    }
    reply = context.client.post(
        f"/api/v1/inbox/conversations/{detail['id']}/reply",
        headers=reply_headers,
        json={"text": "أيوة متاح خلال 2-4 أيام عمل."},
    )
    assert reply.status_code == 202, reply.text
    assert reply.json()["status"] == "queued"

    duplicate = context.client.post(
        f"/api/v1/inbox/conversations/{detail['id']}/reply",
        headers=reply_headers,
        json={"text": "أيوة متاح خلال 2-4 أيام عمل."},
    )
    assert duplicate.status_code == 202, duplicate.text
    assert duplicate.json()["id"] == reply.json()["id"]

    with context.session_factory() as session:
        queued_audits = session.scalars(
            select(AuditEventModel).where(
                AuditEventModel.action == "outbound_message.queued",
                AuditEventModel.entity_type == "message",
                AuditEventModel.entity_id == str(reply.json()["id"]),
            )
        ).all()
    assert len(queued_audits) == 1
    assert queued_audits[0].actor == "merchant@example.com"
    assert queued_audits[0].metadata_json["conversation_id"] == detail["id"]

    conflicting_retry = context.client.post(
        f"/api/v1/inbox/conversations/{detail['id']}/reply",
        headers=reply_headers,
        json={"text": "نص مختلف لنفس مفتاح الطلب"},
    )
    assert conflicting_retry.status_code == 409

    # The demo adapter delivers when the job queue drains.
    assert context.container.job_queue.run_due_jobs() >= 1
    after = context.client.get(f"/api/v1/inbox/conversations/{detail['id']}").json()
    outbound = [m for m in after["messages"] if m["direction"] == "outbound"]
    assert len([m for m in outbound if m["id"] == reply.json()["id"]]) == 1
    assert outbound[-1]["status"] == "sent"
    assert outbound[-1]["external_id"].startswith("demo-")
    assert after["unread_count"] == 0

    with context.session_factory() as session:
        sent_audits = session.scalars(
            select(AuditEventModel).where(
                AuditEventModel.action == "outbound_message.sent",
                AuditEventModel.entity_type == "message",
                AuditEventModel.entity_id == str(reply.json()["id"]),
            )
        ).all()
    assert len(sent_audits) == 1
    assert sent_audits[0].actor == "system"


def test_unfinished_delivery_attempt_requires_manual_reconciliation(
    authenticated: tuple[TestContext, dict[str, str]],
) -> None:
    context, headers = authenticated
    detail = _simulate(context, headers, "هل المنتج متاح؟")
    reply = context.client.post(
        f"/api/v1/inbox/conversations/{detail['id']}/reply",
        headers={**headers, "Idempotency-Key": f"ambiguous-{uuid.uuid4().hex}"},
        json={"text": "نعم، المنتج متاح الآن."},
    )
    assert reply.status_code == 202, reply.text
    message_id = int(reply.json()["id"])

    with context.session_factory() as session:
        attempt = begin_external_operation(
            session,
            store_id=context.container.settings.demo_store_id,
            operation_key=f"outbound-message:{message_id}",
            operation_type="channel.send_message",
            entity_type="message",
            entity_id=str(message_id),
        )
        assert attempt.should_execute is True

    assert context.container.job_queue.run_due_jobs() >= 1
    after = context.client.get(f"/api/v1/inbox/conversations/{detail['id']}").json()
    actual = next(message for message in after["messages"] if message["id"] == message_id)
    assert actual["status"] == "delivery_unknown"
    assert actual["external_id"] is None
    assert actual["error_message"] == "provider_outcome_unknown_manual_review_required"

    with context.session_factory() as session:
        audits = session.scalars(
            select(AuditEventModel).where(
                AuditEventModel.action == "outbound_message.delivery_unknown",
                AuditEventModel.entity_id == str(message_id),
            )
        ).all()
    assert len(audits) == 1
    assert audits[0].metadata_json["attempt_id"] == attempt.attempt_id


def test_transport_failure_is_visible_and_never_automatically_resent(
    authenticated: tuple[TestContext, dict[str, str]], monkeypatch
) -> None:
    context, headers = authenticated
    detail = _simulate(context, headers, "هل الشحن متاح؟")
    reply = context.client.post(
        f"/api/v1/inbox/conversations/{detail['id']}/reply",
        headers={**headers, "Idempotency-Key": f"transport-{uuid.uuid4().hex}"},
        json={"text": "سأراجع حالة الشحن."},
    )
    assert reply.status_code == 202, reply.text
    message_id = int(reply.json()["id"])
    provider_calls: list[str] = []

    class AmbiguousAdapter:
        def send_text(self, credentials, recipient, text):
            del credentials, recipient, text
            provider_calls.append("send")
            return SendResult(
                success=False,
                error_code="transport_error",
                error_message="provider connection ended before a response",
            )

    monkeypatch.setattr(
        "app.services.conversations.resolve_adapter", lambda channel_type, mode: AmbiguousAdapter()
    )
    assert context.container.job_queue.run_due_jobs() >= 1
    # The job succeeds in a manual-reconciliation state; it is never auto-requeued.
    assert context.container.job_queue.run_due_jobs() == 0
    assert provider_calls == ["send"]

    after = context.client.get(f"/api/v1/inbox/conversations/{detail['id']}").json()
    actual = next(message for message in after["messages"] if message["id"] == message_id)
    assert actual["status"] == "delivery_unknown"

    with context.session_factory() as session:
        operation = session.scalar(
            select(ExternalOperationModel).where(
                ExternalOperationModel.operation_key == f"outbound-message:{message_id}"
            )
        )
        assert operation is not None
        assert operation.status == OUTCOME_UNKNOWN
        assert operation.attempts == 1


def test_reply_requires_an_idempotency_key(
    authenticated: tuple[TestContext, dict[str, str]],
) -> None:
    context, headers = authenticated
    detail = _simulate(context, headers, "رسالة تجريبية")

    response = context.client.post(
        f"/api/v1/inbox/conversations/{detail['id']}/reply",
        headers=headers,
        json={"text": "رد تجريبي"},
    )

    assert response.status_code == 422


def test_manage_status_priority_tags_and_notes(
    authenticated: tuple[TestContext, dict[str, str]],
) -> None:
    context, headers = authenticated
    detail = _simulate(context, headers, "عايز أعرف أسعار الشواحن")
    updated = context.client.patch(
        f"/api/v1/inbox/conversations/{detail['id']}",
        headers=headers,
        json={"status": "pending", "priority": "high", "tags": ["شواحن", "متابعة"]},
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["status"] == "pending"
    assert body["priority"] == "high"
    assert body["tags"] == ["شواحن", "متابعة"]

    note = context.client.post(
        f"/api/v1/inbox/conversations/{detail['id']}/notes",
        headers=headers,
        json={"text": "العميل بيقارن الأسعار — ملاحظة داخلية."},
    )
    assert note.status_code == 200
    assert note.json()["sender_type"] == "note"

    filtered = context.client.get("/api/v1/inbox/conversations?status_filter=pending")
    assert any(item["id"] == detail["id"] for item in filtered.json()["conversations"])


def test_inbox_is_tenant_isolated(context: TestContext) -> None:
    headers = context.login()
    mine = _simulate(context, headers, "رسالة للمتجر التجريبي فقط")
    register = context.client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Inbox Rival",
            "store_name": "Rival Inbox Store",
            "email": f"inbox-{uuid.uuid4().hex[:8]}@rival.example",
            "password": "another-strong-pass-123",
        },
    )
    assert register.status_code == 201
    listing = context.client.get("/api/v1/inbox/conversations")
    assert listing.json()["conversations"] == []
    foreign = context.client.get(f"/api/v1/inbox/conversations/{mine['id']}")
    assert foreign.status_code == 404
    context.login()
