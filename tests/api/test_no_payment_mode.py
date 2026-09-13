from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.db.models import AuditEventModel, SubscriptionModel, UsageRecordModel
from app.domain.errors import QuotaExceededError
from app.services.billing import check_and_increment
from tests.conftest import TestContext


def test_free_access_is_server_authoritative_and_never_creates_checkout(
    context: TestContext,
) -> None:
    suffix = uuid.uuid4().hex[:10]
    email = f"free-{suffix}@example.com"
    settings = context.container.settings
    original_mode = settings.free_access_mode
    settings.free_access_mode = True
    try:
        registration = context.client.post(
            "/api/v1/auth/register",
            json={
                "organization_name": f"Free Access {suffix}",
                "store_name": f"Free Store {suffix}",
                "email": email,
                "password": "Correct-Horse-Free-Password9!",
                "full_name": "Free Access Owner",
            },
        )
        assert registration.status_code == 201, registration.text
        user = registration.json()["user"]
        assert user["role"] == "owner"

        capabilities = context.client.get("/api/v1/billing/capabilities")
        assert capabilities.status_code == 200
        assert capabilities.json() == {
            "provider": "internal",
            "status": "free_access",
            "free_access": True,
            "checkout_available": False,
            "portal_available": False,
        }

        subscription = context.client.get("/api/v1/billing/subscription")
        assert subscription.status_code == 200
        assert subscription.json()["plan"]["key"] == "growth"
        assert subscription.json()["status"] == "active"
        assert subscription.json()["provider"] == "internal"
        assert subscription.json()["trial_end"] is None

        csrf = registration.json()["csrf_token"]
        plan_change = context.client.post(
            "/api/v1/billing/subscription",
            headers={"X-CSRF-Token": csrf},
            json={"plan_key": "pro"},
        )
        assert plan_change.status_code == 409
        assert plan_change.json()["error"]["details"] == {
            "free_access": True,
            "checkout_created": False,
        }
        portal = context.client.post(
            "/api/v1/billing/portal",
            headers={"X-CSRF-Token": csrf},
        )
        assert portal.status_code == 409
        assert portal.json()["error"]["details"] == {"free_access": True}

        products = context.client.get("/api/v1/products")
        assert products.status_code == 200
        assert products.json() == []

        with context.session_factory() as session:
            row = session.scalar(
                select(SubscriptionModel).where(
                    SubscriptionModel.organization_id == user["organization_id"]
                )
            )
            assert row is not None
            audit = session.scalar(
                select(AuditEventModel).where(
                    AuditEventModel.organization_id == user["organization_id"],
                    AuditEventModel.action == "free_access_granted",
                )
            )
            assert audit is not None
            assert audit.metadata_json["payment_required"] is False
    finally:
        settings.free_access_mode = original_mode


def test_free_access_keeps_growth_quota_enforcement(context: TestContext) -> None:
    suffix = uuid.uuid4().hex[:10]
    email = f"quota-{suffix}@example.com"
    settings = context.container.settings
    original_mode = settings.free_access_mode
    settings.free_access_mode = True
    try:
        registration = context.client.post(
            "/api/v1/auth/register",
            json={
                "organization_name": f"Quota {suffix}",
                "store_name": f"Quota Store {suffix}",
                "email": email,
                "password": "Correct-Horse-Quota-Password9!",
                "full_name": "Quota Owner",
            },
        )
        assert registration.status_code == 201, registration.text
        user = registration.json()["user"]
        now = datetime.now(UTC)
        period_key = f"{now.year:04d}-{now.month:02d}"
        with context.session_factory.begin() as session:
            session.add(
                UsageRecordModel(
                    organization_id=user["organization_id"],
                    store_id=user["store_id"],
                    metric="conversations",
                    period_key=period_key,
                    quantity=5000,
                )
            )
        with (
            context.session_factory.begin() as session,
            pytest.raises(QuotaExceededError),
        ):
            check_and_increment(session, user["store_id"], "conversations")
    finally:
        settings.free_access_mode = original_mode


def test_login_reconciles_an_existing_trial_to_free_access(context: TestContext) -> None:
    suffix = uuid.uuid4().hex[:10]
    email = f"reconcile-{suffix}@example.com"
    password = "Correct-Horse-Reconcile-Password9!"
    settings = context.container.settings
    original_mode = settings.free_access_mode
    settings.free_access_mode = False
    try:
        registration = context.client.post(
            "/api/v1/auth/register",
            json={
                "organization_name": f"Reconcile {suffix}",
                "store_name": f"Reconcile Store {suffix}",
                "email": email,
                "password": password,
                "full_name": "Reconcile Owner",
            },
        )
        assert registration.status_code == 201
        trial = context.client.get("/api/v1/billing/subscription").json()
        assert trial["status"] == "trialing"
        assert trial["trial_end"] is not None
        logout = context.client.post(
            "/api/v1/auth/logout",
            headers={"X-CSRF-Token": registration.json()["csrf_token"]},
        )
        assert logout.status_code == 200

        settings.free_access_mode = True
        login = context.client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login.status_code == 200
        subscription = context.client.get("/api/v1/billing/subscription").json()
        assert subscription["status"] == "active"
        assert subscription["trial_end"] is None
        assert subscription["plan"]["key"] == "growth"

        context.client.post(
            "/api/v1/auth/logout",
            headers={"X-CSRF-Token": login.json()["csrf_token"]},
        )
        second_login = context.client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert second_login.status_code == 200
        with context.session_factory() as session:
            organization_id = second_login.json()["user"]["organization_id"]
            audits = session.scalars(
                select(AuditEventModel).where(
                    AuditEventModel.organization_id == organization_id,
                    AuditEventModel.action == "free_access_granted",
                )
            ).all()
            assert len(audits) == 1
    finally:
        settings.free_access_mode = original_mode
