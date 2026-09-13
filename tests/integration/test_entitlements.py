"""Internal trials, feature gates, and quota concurrency."""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.db.models import (
    OrganizationModel,
    StoreModel,
    SubscriptionModel,
    UsageRecordModel,
)
from app.domain.errors import QuotaExceededError
from app.services.billing import (
    check_and_increment,
    ensure_subscription,
    require_feature,
)
from tests.conftest import TestContext


def _tenant(context: TestContext) -> tuple[str, str]:
    suffix = uuid.uuid4().hex[:10]
    organization_id = f"org-ent-{suffix}"
    store_id = f"store-ent-{suffix}"
    with context.session_factory.begin() as session:
        session.add(
            OrganizationModel(
                id=organization_id,
                name=f"Entitlement {suffix}",
                plan="starter",
            )
        )
        session.add(
            StoreModel(
                id=store_id,
                organization_id=organization_id,
                slug=f"ent-{suffix}",
                name=f"Entitlement {suffix}",
            )
        )
    return organization_id, store_id


def test_new_tenant_gets_growth_internal_trial_and_feature_gate(
    context: TestContext,
) -> None:
    organization_id, store_id = _tenant(context)
    with context.session_factory.begin() as session:
        subscription = ensure_subscription(session, organization_id)
        assert subscription.provider == "internal"
        assert subscription.status == "trialing"
        assert subscription.plan_key == "growth"
        assert subscription.trial_end is not None
        require_feature(session, store_id, "automations")

        subscription.plan_key = "starter"
        with pytest.raises(QuotaExceededError):
            require_feature(session, store_id, "automations")

        subscription.status = "trialing"
        subscription.trial_end = datetime.now(UTC) - timedelta(seconds=1)
        with pytest.raises(QuotaExceededError):
            require_feature(session, store_id, "catalog")


def test_concurrent_quota_increment_allows_only_remaining_capacity(
    context: TestContext,
) -> None:
    organization_id, store_id = _tenant(context)
    now = datetime.now(UTC)
    period_key = f"{now.year:04d}-{now.month:02d}"
    with context.session_factory.begin() as session:
        subscription = ensure_subscription(session, organization_id)
        subscription.plan_key = "starter"
        subscription.status = "active"
        subscription.provider = "internal"
        session.add(
            UsageRecordModel(
                organization_id=organization_id,
                store_id=store_id,
                metric="ai_operations",
                period_key=period_key,
                quantity=199,
            )
        )

    def increment() -> str:
        try:
            with context.session_factory.begin() as session:
                check_and_increment(session, store_id, "ai_operations")
            return "accepted"
        except QuotaExceededError:
            return "blocked"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: increment(), range(2)))

    assert sorted(results) == ["accepted", "blocked"]
    with context.session_factory() as session:
        subscription = session.scalar(
            select(SubscriptionModel).where(SubscriptionModel.organization_id == organization_id)
        )
        assert subscription is not None
        usage = session.scalar(
            select(UsageRecordModel).where(
                UsageRecordModel.organization_id == organization_id,
                UsageRecordModel.metric == "ai_operations",
            )
        )
        assert usage is not None
        assert usage.quantity == 200
