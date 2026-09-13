from __future__ import annotations

import hashlib
import hmac
import json
import uuid

import pytest

from tests.conftest import TestContext, onboard_product


@pytest.mark.e2e
def test_merchant_journey_from_login_to_fake_publish(context: TestContext) -> None:
    headers = context.login()
    product_id = f"E2E{uuid.uuid4().hex[:8]}"
    onboarded = onboard_product(context, headers, product_id)
    assert onboarded["status"] == "draft"
    reviewed = context.client.patch(
        f"/api/v1/products/{product_id}",
        headers=headers,
        json={
            "features": ["Bluetooth", "microphone"],
            "customer_benefits": ["مناسب للمكالمات"],
            "description": "منتج اختباري للمكالمات.",
        },
    )
    assert reviewed.json()["status"] == "reviewed"
    assert (
        context.client.post(f"/api/v1/products/{product_id}/activate", headers=headers).json()[
            "status"
        ]
        == "active"
    )
    pack = context.client.post(
        f"/api/v1/products/{product_id}/marketing-packs", headers=headers
    ).json()
    assert pack["facebook_message"] != pack["instagram_caption"]
    approved = context.client.post(f"/api/v1/marketing-packs/{pack['id']}/approve", headers=headers)
    assert approved.json()["status"] == "approved"
    published = context.client.post(
        f"/api/v1/marketing-packs/{pack['id']}/publish",
        headers={**headers, "Idempotency-Key": f"e2e-{uuid.uuid4().hex}"},
        json={"platforms": ["facebook", "instagram"]},
    )
    assert published.status_code == 200
    assert [item["platform"] for item in published.json()["results"]] == [
        "facebook",
        "instagram",
    ]


@pytest.mark.e2e
def test_customer_journey_returns_copyable_grounded_answer(context: TestContext) -> None:
    context.login()
    response = context.client.post(
        "/api/v1/sales/assist",
        json={"message": "I need headphones for calls under 1500 EGP"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert 1 <= len(payload["recommendations"]) <= 3
    assert payload["reply"]
    assert all(
        f"product:{item['product_id']}" in payload["citations"]
        for item in payload["recommendations"]
    )


@pytest.mark.e2e
def test_full_revenue_autopilot_demo_journey(context: TestContext) -> None:
    suffix = uuid.uuid4().hex[:8]
    email = f"journey-{suffix}@example.com"
    registered = context.client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": f"Journey Org {suffix}",
            "store_name": f"Journey Store {suffix}",
            "email": email,
            "password": "journey-strong-password-123",
            "full_name": "Journey Owner",
        },
    )
    assert registered.status_code == 201, registered.text
    store_id = registered.json()["user"]["store_id"]
    headers = {"X-CSRF-Token": registered.json()["csrf_token"]}
    upgraded = context.client.post(
        "/api/v1/billing/subscription",
        headers=headers,
        json={"plan_key": "growth"},
    )
    assert upgraded.status_code == 200

    product_id = f"JRN{suffix}"
    onboarded = onboard_product(context, headers, product_id, price="199.00", stock="2")
    reviewed = context.client.patch(
        f"/api/v1/products/{product_id}",
        headers=headers,
        json={
            "features": ["Bluetooth", "microphone", "comfortable"],
            "customer_benefits": ["مناسب للمكالمات"],
            "description": "سماعة اقتصادية للمكالمات.",
        },
    )
    assert reviewed.status_code == 200
    activated = context.client.post(f"/api/v1/products/{product_id}/activate", headers=headers)
    assert activated.status_code == 200
    assert activated.json()["status"] == "active"
    assert onboarded["name"]

    oauth = context.client.post(
        "/api/v1/integrations/meta/channels/oauth/start", headers=headers
    ).json()
    exchange = context.client.post(
        "/api/v1/integrations/meta/channels/oauth/exchange",
        headers=headers,
        json={"code": "demo", "state": oauth["state"]},
    ).json()
    account = exchange["accounts"][0]
    connected = context.client.post(
        "/api/v1/integrations/meta/channels/oauth/connect",
        headers=headers,
        json={
            "transaction_id": exchange["transaction_id"],
            "page_id": account["page_id"],
            "instagram_account_id": account["instagram_account_id"],
        },
    )
    assert connected.status_code == 200, connected.text
    messenger = next(item for item in connected.json() if item["channel_type"] == "messenger")

    message_text = f"عايز سماعة مكالمات أقل من 250 جنيه {suffix}"
    webhook_payload = {
        "object": "page",
        "entry": [
            {
                "id": "demo-page",
                "messaging": [
                    {
                        "sender": {"id": f"customer-{suffix}"},
                        "recipient": {"id": "demo-page"},
                        "message": {
                            "mid": f"mid.journey.{suffix}",
                            "text": message_text,
                        },
                    }
                ],
            }
        ],
    }
    raw = json.dumps(webhook_payload, separators=(",", ":")).encode()
    signature = "sha256=" + hmac.new(b"demo-meta-app-secret", raw, hashlib.sha256).hexdigest()
    received = context.client.post(
        f"/webhooks/meta/{messenger['channel_id']}",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": signature,
        },
    )
    assert received.status_code == 200, received.text
    conversations = context.client.get("/api/v1/inbox/conversations", headers=headers).json()[
        "conversations"
    ]
    conversation = next(item for item in conversations if suffix in item["last_message_preview"])

    recommendation = context.client.post(
        "/api/v1/sales/assist",
        headers=headers,
        json={"message": "I need headphones for calls under 250 EGP"},
    )
    assert recommendation.status_code == 200, recommendation.text
    assert product_id in [item["product_id"] for item in recommendation.json()["recommendations"]]

    order = context.client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "conversation_id": conversation["id"],
            "items": [{"product_id": product_id, "quantity": 1}],
            "discount": "0",
            "shipping": {"city": "Cairo", "address": "Demo address"},
        },
    )
    assert order.status_code == 201, order.text

    scan = context.client.post("/api/v1/opportunities/scan", headers=headers)
    assert scan.status_code == 202
    assert context.container.job_queue.run_due_jobs() >= 1
    opportunities = context.client.get("/api/v1/opportunities", headers=headers).json()
    opportunity = next(item for item in opportunities if product_id in item["related_product_ids"])
    approved = context.client.post(
        f"/api/v1/opportunities/{opportunity['id']}/decision",
        headers=headers,
        json={"decision": "approve", "realized_revenue": "0"},
    )
    assert approved.json()["status"] == "awaiting_approval"
    executed = context.client.post(
        f"/api/v1/opportunities/{opportunity['id']}/decision",
        headers=headers,
        json={"decision": "execute", "realized_revenue": "0"},
    )
    assert executed.json()["status"] == "executed"

    automation = context.client.post(
        "/api/v1/automations",
        headers=headers,
        json={
            "name": "Journey follow-up",
            "trigger_type": "scheduled",
            "actions": [
                {
                    "action_type": "draft_reply",
                    "config": {"text": "Follow up on the journey order"},
                }
            ],
        },
    )
    assert automation.status_code == 201, automation.text
    event = context.client.post(
        "/api/v1/automations/events",
        headers=headers,
        json={
            "trigger_type": "scheduled",
            "event_key": f"journey-{suffix}",
            "event": {"conversation_id": conversation["id"]},
        },
    )
    assert event.json()["runs_created"] == 1
    assert context.container.job_queue.run_due_jobs() >= 1
    runs = context.client.get("/api/v1/automations/runs", headers=headers).json()
    assert any(
        run["automation_id"] == automation.json()["id"] and run["status"] == "succeeded"
        for run in runs
    )

    content = context.client.post(
        "/api/v1/studio/content/generate",
        headers=headers,
        json={
            "product_id": product_id,
            "content_format": "sales_post",
            "platform": "facebook",
            "tone": "friendly",
        },
    )
    assert content.status_code == 201, content.text
    content_id = content.json()["id"]
    approved_content = context.client.post(
        f"/api/v1/studio/content/{content_id}/approve", headers=headers
    )
    assert approved_content.status_code == 200, approved_content.text
    queued = context.client.post(f"/api/v1/studio/content/{content_id}/publish", headers=headers)
    assert queued.status_code == 200
    assert context.container.job_queue.run_due_jobs() >= 1
    published = context.client.get("/api/v1/studio/content", headers=headers).json()
    assert next(item for item in published if item["id"] == content_id)["status"] == "published"

    analytics = context.client.get("/api/v1/analytics", headers=headers)
    assert analytics.status_code == 200
    assert analytics.json()["content_published"] >= 1
    assert analytics.json()["conversation_volume"] >= 1

    demo_headers = context.login()
    assert (
        context.client.get(f"/api/v1/orders/{order.json()['id']}", headers=demo_headers).status_code
        == 404
    )
    assert (
        context.client.patch(
            f"/api/v1/studio/content/{content_id}",
            headers=demo_headers,
            json={"caption": "cross tenant"},
        ).status_code
        == 404
    )
    assert store_id != "demo-store"
