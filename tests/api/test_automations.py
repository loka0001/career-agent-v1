from __future__ import annotations

from sqlalchemy import select

from app.db.models import ConversationModel, ProductModel


def test_automation_approval_execution_and_duplicate_suppression(authenticated) -> None:
    context, headers = authenticated
    with context.session_factory() as session:
        conversation_id = session.scalar(
            select(ConversationModel.id)
            .where(ConversationModel.store_id == "demo-store")
            .order_by(ConversationModel.id)
        )
        assert conversation_id is not None
    created = context.client.post(
        "/api/v1/automations",
        headers=headers,
        json={
            "name": "Draft follow-up",
            "trigger_type": "scheduled",
            "conditions": [
                {"field": "priority", "operator": "eq", "value": "high"}
            ],
            "actions": [
                {
                    "action_type": "draft_reply",
                    "config": {"text": "Follow up with this customer"},
                }
            ],
            "delay_seconds": 0,
            "approval_required": True,
            "is_enabled": True,
        },
    )
    assert created.status_code == 201, created.text
    automation_id = created.json()["id"]
    event = {
        "trigger_type": "scheduled",
        "event_key": "scheduled-test-1",
        "event": {"priority": "high", "conversation_id": conversation_id},
    }
    emitted = context.client.post(
        "/api/v1/automations/events", headers=headers, json=event
    )
    assert emitted.status_code == 200
    assert emitted.json()["runs_created"] == 1
    duplicate = context.client.post(
        "/api/v1/automations/events", headers=headers, json=event
    )
    assert duplicate.json()["runs_created"] == 0

    runs = context.client.get(
        "/api/v1/automations/runs",
        headers=headers,
        params={"automation_id": automation_id},
    )
    assert runs.status_code == 200
    run = runs.json()[0]
    assert run["status"] == "awaiting_approval"
    approved = context.client.post(
        f"/api/v1/automations/runs/{run['id']}/approve", headers=headers
    )
    assert approved.status_code == 200
    assert context.container.job_queue.run_due_jobs() >= 1
    completed = context.client.get(
        "/api/v1/automations/runs",
        headers=headers,
        params={"automation_id": automation_id},
    ).json()[0]
    assert completed["status"] == "succeeded"
    conversation = context.client.get(
        f"/api/v1/inbox/conversations/{conversation_id}", headers=headers
    ).json()
    assert conversation["messages"][-1]["sender_type"] == "note"
    assert "Automation draft" in conversation["messages"][-1]["body"]

    disabled = context.client.post(
        f"/api/v1/automations/{automation_id}/disable", headers=headers
    )
    assert disabled.status_code == 200
    assert disabled.json()["is_enabled"] is False


def test_ready_made_automation_template_is_idempotent(authenticated) -> None:
    context, headers = authenticated
    first = context.client.post(
        "/api/v1/automations/templates/low_stock_alert", headers=headers
    )
    second = context.client.post(
        "/api/v1/automations/templates/low_stock_alert", headers=headers
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    context.client.post(
        f"/api/v1/automations/{first.json()['id']}/disable", headers=headers
    )


def test_automation_creates_real_order_and_content(authenticated) -> None:
    context, headers = authenticated
    with context.session_factory() as session:
        conversation_id = session.scalar(
            select(ConversationModel.id)
            .where(ConversationModel.store_id == "demo-store")
            .order_by(ConversationModel.id)
        )
        product_id = session.scalar(
            select(ProductModel.product_id)
            .where(
                ProductModel.store_id == "demo-store",
                ProductModel.status == "active",
                ProductModel.stock > 0,
            )
            .order_by(ProductModel.id)
        )
        assert conversation_id is not None
        assert product_id is not None

    created = context.client.post(
        "/api/v1/automations",
        headers=headers,
        json={
            "name": "Order and content proof",
            "trigger_type": "scheduled",
            "conditions": [],
            "actions": [
                {
                    "action_type": "create_draft_order",
                    "config": {"product_id": product_id, "quantity": 1},
                },
                {
                    "action_type": "generate_content",
                    "config": {
                        "product_id": product_id,
                        "content_format": "sales_post",
                        "platform": "facebook",
                    },
                },
            ],
            "delay_seconds": 0,
            "approval_required": False,
            "is_enabled": True,
        },
    )
    assert created.status_code == 201, created.text
    automation_id = created.json()["id"]
    emitted = context.client.post(
        "/api/v1/automations/events",
        headers=headers,
        json={
            "trigger_type": "scheduled",
            "event_key": "order-content-proof",
            "event": {
                "conversation_id": conversation_id,
                "product_id": product_id,
            },
        },
    )
    assert emitted.status_code == 200, emitted.text
    assert emitted.json()["runs_created"] == 1
    assert context.container.job_queue.run_due_jobs() >= 2

    orders = context.client.get("/api/v1/orders", headers=headers)
    assert orders.status_code == 200
    assert any("Created by automation run" in order["notes"] for order in orders.json())
    content = context.client.get("/api/v1/studio/content", headers=headers)
    assert content.status_code == 200
    assert any("[automation:" in item["title"] for item in content.json())
    context.client.post(
        f"/api/v1/automations/{automation_id}/disable", headers=headers
    )
