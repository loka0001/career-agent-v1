from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from app.db.models import StoreModel, UsageRecordModel


def test_billing_catalog_subscription_and_enforced_ai_quota(authenticated) -> None:
    context, headers = authenticated

    plans = context.client.get("/api/v1/billing/plans", headers=headers)
    assert plans.status_code == 200, plans.text
    assert {plan["key"] for plan in plans.json()} == {"starter", "growth", "pro"}

    current = context.client.get("/api/v1/billing/subscription", headers=headers)
    assert current.status_code == 200, current.text
    assert current.json()["plan"]["key"] == "growth"

    starter = context.client.post(
        "/api/v1/billing/subscription",
        headers=headers,
        json={"plan_key": "starter"},
    )
    assert starter.status_code == 200, starter.text
    assert starter.json()["provider"] == "demo"
    assert starter.json()["plan"]["key"] == "starter"

    now = datetime.now(UTC)
    period_key = f"{now.year:04d}-{now.month:02d}"
    with context.session_factory() as session:
        store = session.get(StoreModel, "demo-store")
        assert store is not None
        usage = session.scalar(
            select(UsageRecordModel).where(
                UsageRecordModel.organization_id == store.organization_id,
                UsageRecordModel.store_id == store.id,
                UsageRecordModel.metric == "ai_operations",
                UsageRecordModel.period_key == period_key,
            )
        )
        if usage is None:
            usage = UsageRecordModel(
                organization_id=str(store.organization_id),
                store_id=store.id,
                metric="ai_operations",
                period_key=period_key,
                quantity=200,
            )
            session.add(usage)
        else:
            usage.quantity = 200
        session.commit()

    blocked = context.client.post(
        "/api/v1/sales/assist",
        headers=headers,
        json={"message": "رشح لي منتج مناسب"},
    )
    assert blocked.status_code == 402, blocked.text
    assert blocked.json()["error"]["code"] == "quota_exceeded"
    assert blocked.json()["error"]["details"]["metric"] == "ai_operations"
    assert blocked.json()["error"]["details"]["upgrade_required"] is True

    restored = context.client.post(
        "/api/v1/billing/subscription",
        headers=headers,
        json={"plan_key": "growth"},
    )
    assert restored.status_code == 200, restored.text
