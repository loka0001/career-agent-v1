"""Privacy export, retention, deletion, and Meta callback journeys."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta

from pydantic import SecretStr
from sqlalchemy import select

from app.db.models import (
    BackgroundJobModel,
    CustomerIdentityModel,
    CustomerModel,
    DataDeletionRequestModel,
    ExternalOperationModel,
    SalesQueryModel,
    StoreModel,
    UserModel,
)
from app.repositories.tenant_repository import TenantRepository
from app.security import hash_password
from app.services.privacy import request_account_deletion
from tests.conftest import TestContext


def test_store_export_retention_and_legal_policies(
    authenticated: tuple[TestContext, dict[str, str]],
) -> None:
    context, headers = authenticated
    exported = context.client.get("/api/v1/privacy/export", headers=headers)
    assert exported.status_code == 200, exported.text
    assert exported.json()["store"]["id"] == "demo-store"
    assert "credentials_json" not in exported.text

    with context.session_factory.begin() as session:
        old_query = SalesQueryModel(
            store_id="demo-store",
            message="sha256:old",
            parsed_need_json={},
            recommended_product_ids_json=[],
            response_text="sha256:old-response",
            citations_json=[],
            created_at=datetime.now(UTC) - timedelta(days=181),
        )
        current_query = SalesQueryModel(
            store_id="demo-store",
            message="sha256:current",
            parsed_need_json={},
            recommended_product_ids_json=[],
            response_text="sha256:current-response",
            citations_json=[],
        )
        session.add_all([old_query, current_query])
        session.flush()
        old_query_id = old_query.id
        current_query_id = current_query.id

    updated = context.client.put(
        "/api/v1/privacy/retention",
        headers=headers,
        json={"message_days": 180, "media_days": 14, "event_days": 365},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["media_days"] == 14
    assert context.container.job_queue.run_due_jobs(limit=10) >= 1
    with context.session_factory() as session:
        assert session.get(SalesQueryModel, old_query_id) is None
        assert session.get(SalesQueryModel, current_query_id) is not None

    privacy = context.client.get("/api/v1/legal/privacy")
    terms = context.client.get("/api/v1/legal/terms")
    assert privacy.status_code == 200
    assert terms.status_code == 200
    assert privacy.json()["certifications"] == []


def test_deletion_requires_password_confirmation(
    authenticated: tuple[TestContext, dict[str, str]],
) -> None:
    context, headers = authenticated
    response = context.client.post(
        "/api/v1/privacy/account-deletion",
        headers=headers,
        json={"password": "incorrect-password!", "confirmation": "DELETE"},
    )
    assert response.status_code == 401


def test_account_deletion_worker_anonymizes_owner_and_owned_store(
    context: TestContext,
) -> None:
    password = "Delete-Account-123!"
    with context.session_factory.begin() as session:
        user, organization, store = TenantRepository(session).create_tenant(
            organization_name="Deletion Org",
            store_name="Deletion Store",
            email="delete-owner@example.com",
            password_hash=hash_password(password),
        )
        user.email_verified_at = datetime.now(UTC)
        request = request_account_deletion(
            session,
            user_id=user.id,
            organization_id=organization.id,
            store_id=store.id,
            password=password,
        )
        session.add(
            ExternalOperationModel(
                store_id=store.id,
                operation_key="deletion-ledger-entry",
                operation_type="channel.send_message",
                entity_type="message",
                entity_id="42",
                status="outcome_unknown",
                attempt_id="deletion-ledger-attempt",
            )
        )
        request_id = request.id
        user_id = user.id
        store_id = store.id

    with context.session_factory.begin() as session:
        request = session.get(DataDeletionRequestModel, request_id)
        assert request is not None
        request.execute_after = datetime.now(UTC) - timedelta(seconds=1)
        job = session.scalar(
            select(BackgroundJobModel).where(
                BackgroundJobModel.dedup_key == f"privacy-delete:{request_id}"
            )
        )
        assert job is not None
        job.run_at = datetime.now(UTC) - timedelta(seconds=1)

    assert context.container.job_queue.run_due_jobs(limit=10) >= 1
    with context.session_factory() as session:
        request = session.get(DataDeletionRequestModel, request_id)
        user = session.get(UserModel, user_id)
        store = session.get(StoreModel, store_id)
        assert request is not None and request.status == "completed"
        assert user is not None and user.is_active is False
        assert user.email.endswith("@invalid.local")
        assert store is not None and store.is_active is False
        assert store.deleted_at is not None
        assert (
            session.scalar(
                select(ExternalOperationModel).where(ExternalOperationModel.store_id == store_id)
            )
            is None
        )


def _meta_signed_request(user_id: str, secret: str) -> str:
    payload = (
        base64.urlsafe_b64encode(json.dumps({"user_id": user_id}, separators=(",", ":")).encode())
        .rstrip(b"=")
        .decode()
    )
    signature = (
        base64.urlsafe_b64encode(
            hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest()
        )
        .rstrip(b"=")
        .decode()
    )
    return f"{signature}.{payload}"


def test_meta_data_deletion_callback_is_signed_and_anonymizes_customer(
    context: TestContext,
) -> None:
    external_id = "meta-delete-user-1"
    with context.session_factory.begin() as session:
        customer = CustomerModel(
            store_id="demo-store",
            display_name="Meta Delete",
            phone="+201000000001",
            email="meta-delete@example.com",
        )
        session.add(customer)
        session.flush()
        session.add(
            CustomerIdentityModel(
                store_id="demo-store",
                customer_id=customer.id,
                channel_type="messenger",
                external_id=external_id,
            )
        )
        customer_id = customer.id

    secret = "meta-deletion-test-secret"
    original = context.container.settings.meta_app_secret
    context.container.settings.meta_app_secret = SecretStr(secret)
    try:
        rejected = context.client.post(
            "/webhooks/meta/data-deletion",
            data={"signed_request": "invalid.request"},
        )
        assert rejected.status_code == 401, rejected.text
        accepted = context.client.post(
            "/webhooks/meta/data-deletion",
            data={"signed_request": _meta_signed_request(external_id, secret)},
        )
        assert accepted.status_code == 200, accepted.text
        confirmation_code = accepted.json()["confirmation_code"]
    finally:
        context.container.settings.meta_app_secret = original

    assert context.container.job_queue.run_due_jobs(limit=10) >= 1
    public_status = context.client.get(f"/api/v1/privacy/public-deletions/{confirmation_code}")
    assert public_status.status_code == 200
    assert public_status.json()["status"] == "completed"
    with context.session_factory() as session:
        customer = session.get(CustomerModel, customer_id)
        assert customer is not None
        assert customer.email is None
        assert customer.phone is None
