"""Signed queue drain and operator-only operational controls."""

from __future__ import annotations

import hmac
import secrets
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Header, Query, Request
from sqlalchemy import func, select, text

from app.api.dependencies import (
    ContainerDependency,
    DatabaseDependency,
    OperatorReadUser,
    OperatorUser,
)
from app.db.models import (
    AIUsageRecordModel,
    AuditEventModel,
    BackgroundJobModel,
    ProviderConnectionModel,
    ProviderWebhookEventModel,
    StoreModel,
    StripeEventModel,
    SubscriptionModel,
    UsageRecordModel,
)
from app.domain.errors import AuthenticationError, NotFoundError
from app.domain.models import StoreSuspensionInput
from app.services.job_queue import enqueue_job, job_handler

router = APIRouter(tags=["operations"])
_LOCAL_DRAIN_LOCK = threading.Lock()
_ADVISORY_LOCK_ID = 76072825
_DIAGNOSTIC_JOB_PREFIX = "operations.diagnostic."
_QUEUE_BACKLOG_ALERT_SECONDS = 900.0
_PROVIDER_ATTENTION_STATUSES = {"degraded", "expired", "action_required"}
_READINESS_ISSUE_CODES = {
    "AI provider is not configured": "ai_provider_missing",
    "SaaS billing is not configured": "billing_provider_missing",
    "Stripe billing credentials or prices are incomplete": "stripe_billing_incomplete",
    "Customer payment provider is not configured": "payment_provider_missing",
    "Stripe customer payment credentials are incomplete": "stripe_payment_incomplete",
    "Transactional email is not configured": "transactional_email_missing",
    "Operator access allowlist is not configured": "operator_allowlist_missing",
    "Cron authentication is not configured": "cron_secret_missing",
    "Integration credential encryption is not configured": "integration_encryption_missing",
    "Persistent background worker runtime is not explicitly enabled": "worker_runtime_missing",
    "External error monitoring is not configured": "external_monitoring_missing",
    "Release SHA is not configured": "release_sha_missing",
    "Meta App credentials are not configured": "meta_app_credentials_missing",
    "WhatsApp Embedded Signup configuration is not configured": "whatsapp_signup_missing",
    "Meta OAuth redirect URL is not production-ready": "meta_oauth_redirect_not_ready",
    "Shopify OAuth redirect URL is not production-ready": "shopify_oauth_redirect_not_ready",
    "External or database-backed media storage is not configured": "media_storage_missing",
    "Malware scanning is not configured": "malware_scanning_missing",
}


def _verify_cron_secret(authorization: str | None, expected: str) -> None:
    supplied = ""
    if authorization and authorization.startswith("Bearer "):
        supplied = authorization.removeprefix("Bearer ").strip()
    if len(expected) < 32 or not hmac.compare_digest(supplied, expected):
        raise AuthenticationError("Invalid internal job credential")


def _diagnostic_audit(
    session: Any,
    *,
    scenario: str,
    marker: str,
) -> None:
    session.add(
        AuditEventModel(
            actor="system",
            action="internal.job.diagnostic.succeeded",
            entity_type="background_job",
            entity_id=marker,
            metadata_json={"scenario": scenario},
        )
    )


def _operational_alert(
    *,
    code: str,
    severity: str,
    status: str,
    message: str,
    details: dict[str, object],
) -> dict[str, object]:
    return {
        "code": code,
        "severity": severity,
        "status": status,
        "message": message,
        "details": details,
    }


def _queue_alerts(
    metrics: dict[str, int | float | None],
    *,
    stale_running: int,
) -> list[dict[str, object]]:
    failed = int(metrics.get("failed") or 0)
    queued = int(metrics.get("queued") or 0)
    oldest_raw = metrics.get("oldest_job_age_seconds")
    oldest_age = float(oldest_raw) if oldest_raw is not None else None
    backlog_firing = oldest_age is not None and oldest_age > _QUEUE_BACKLOG_ALERT_SECONDS
    return [
        _operational_alert(
            code="queue_dead_jobs",
            severity="critical",
            status="firing" if failed > 0 else "ok",
            message=(
                "Dead-lettered jobs require operator replay or investigation."
                if failed > 0
                else "No dead-lettered jobs are present."
            ),
            details={"failed": failed},
        ),
        _operational_alert(
            code="queue_backlog_age",
            severity="warning",
            status="firing" if backlog_firing else "ok",
            message=(
                "The oldest queued job is older than the launch threshold."
                if backlog_firing
                else "Queued jobs are within the launch backlog threshold."
            ),
            details={
                "queued": queued,
                "oldest_job_age_seconds": oldest_age,
                "threshold_seconds": _QUEUE_BACKLOG_ALERT_SECONDS,
            },
        ),
        _operational_alert(
            code="worker_stale_leases",
            severity="critical",
            status="firing" if stale_running > 0 else "ok",
            message=(
                "Running jobs have stale leases and need recovery."
                if stale_running > 0
                else "No stale running job leases are present."
            ),
            details={"stale_running": stale_running},
        ),
    ]


def _configuration_alert(issues: list[str]) -> dict[str, object]:
    issue_codes = sorted(
        {_READINESS_ISSUE_CODES.get(issue, "configuration_issue") for issue in issues}
    )
    return _operational_alert(
        code="production_readiness_incomplete",
        severity="warning",
        status="firing" if issue_codes else "ok",
        message=(
            "Production configuration prerequisites need operator attention."
            if issue_codes
            else "Production configuration prerequisites are satisfied."
        ),
        details={
            "issue_count": len(issues),
            "issues": issue_codes,
        },
    )


@job_handler("operations.diagnostic.success")
def _diagnostic_success(session: Any, payload: dict[str, Any]) -> None:
    _diagnostic_audit(
        session,
        scenario=str(payload.get("scenario", "success")),
        marker=str(payload.get("marker", "")),
    )


@job_handler("operations.diagnostic.retry_once")
def _diagnostic_retry_once(session: Any, payload: dict[str, Any]) -> None:
    dedup_key = str(payload.get("dedup_key", ""))
    job = session.scalar(
        select(BackgroundJobModel).where(BackgroundJobModel.dedup_key == dedup_key)
    )
    if job is not None and job.attempts <= 1:
        raise RuntimeError("controlled diagnostic retry")
    _diagnostic_audit(
        session,
        scenario=str(payload.get("scenario", "retry_once")),
        marker=str(payload.get("marker", "")),
    )


@contextmanager
def _drain_lock(container: Any) -> Iterator[bool]:
    if container.engine.dialect.name == "postgresql":
        with container.engine.connect() as connection:
            acquired = bool(
                connection.scalar(
                    text("SELECT pg_try_advisory_lock(:lock_id)"),
                    {"lock_id": _ADVISORY_LOCK_ID},
                )
            )
            try:
                yield acquired
            finally:
                if acquired:
                    connection.execute(
                        text("SELECT pg_advisory_unlock(:lock_id)"),
                        {"lock_id": _ADVISORY_LOCK_ID},
                    )
    else:
        acquired = _LOCAL_DRAIN_LOCK.acquire(blocking=False)
        try:
            yield acquired
        finally:
            if acquired:
                _LOCAL_DRAIN_LOCK.release()


@router.get("/internal/jobs/drain")
def drain_jobs(
    request: Request,
    container: ContainerDependency,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> dict[str, object]:
    """Drain due work without relying on browser traffic."""

    del request
    _verify_cron_secret(
        authorization,
        container.settings.cron_secret.get_secret_value(),
    )
    with _drain_lock(container) as acquired:
        if not acquired:
            return {
                "status": "already_running",
                "executed": 0,
                "queue": container.job_queue.metrics(),
            }
        recovered = container.job_queue.recover_stale_jobs(
            stale_after_seconds=container.settings.worker_lease_seconds
        )
        executed = container.job_queue.run_due_jobs(limit=limit)
        return {
            "status": "ok",
            "executed": executed,
            "recovered": recovered,
            "queue": container.job_queue.metrics(),
        }


@router.post("/internal/jobs/recover-stale")
def recover_stale_jobs(
    request: Request,
    container: ContainerDependency,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> dict[str, object]:
    """Requeue abandoned jobs without executing pending customer or provider work."""

    del request
    _verify_cron_secret(
        authorization,
        container.settings.cron_secret.get_secret_value(),
    )
    with _drain_lock(container) as acquired:
        if not acquired:
            return {
                "status": "already_running",
                "recovered": 0,
                "queue": container.job_queue.metrics(),
            }
        recovered = container.job_queue.recover_stale_jobs(
            stale_after_seconds=container.settings.worker_lease_seconds
        )
        return {
            "status": "ok",
            "recovered": recovered,
            "queue": container.job_queue.metrics(),
        }


@router.post("/internal/jobs/diagnostics")
def enqueue_job_diagnostic(
    db: DatabaseDependency,
    container: ContainerDependency,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    scenario: Annotated[str, Query(pattern=r"^(success|retry_once)$")] = "success",
    marker: Annotated[
        str | None,
        Query(min_length=6, max_length=80, pattern=r"^[A-Za-z0-9_.:-]+$"),
    ] = None,
    delay_seconds: Annotated[int, Query(ge=0, le=900)] = 0,
) -> dict[str, object]:
    """Enqueue a safe internal diagnostic job for production scheduler verification."""

    _verify_cron_secret(
        authorization,
        container.settings.cron_secret.get_secret_value(),
    )
    actual_marker = marker or secrets.token_urlsafe(12)
    job_type = f"{_DIAGNOSTIC_JOB_PREFIX}{scenario}"
    dedup_key = f"{job_type}:{actual_marker}"
    job = enqueue_job(
        db,
        job_type=job_type,
        payload={
            "scenario": scenario,
            "marker": actual_marker,
            "dedup_key": dedup_key,
        },
        run_at=datetime.now(UTC) + timedelta(seconds=delay_seconds),
        max_attempts=3,
        dedup_key=dedup_key,
    )
    return {
        "status": "queued" if job is not None else "duplicate",
        "job_id": job.id if job is not None else None,
        "scenario": scenario,
        "marker": actual_marker,
        "dedup_key": dedup_key,
        "queue": container.job_queue.metrics(),
    }


@router.get("/internal/jobs/diagnostics")
def job_diagnostic_status(
    db: DatabaseDependency,
    container: ContainerDependency,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    marker: Annotated[
        str,
        Query(min_length=6, max_length=80, pattern=r"^[A-Za-z0-9_.:-]+$"),
    ] = "",
) -> list[dict[str, object]]:
    """Return only diagnostic job status; payloads and secret values stay hidden."""

    _verify_cron_secret(
        authorization,
        container.settings.cron_secret.get_secret_value(),
    )
    rows = db.scalars(
        select(BackgroundJobModel)
        .where(
            BackgroundJobModel.job_type.like(f"{_DIAGNOSTIC_JOB_PREFIX}%"),
            BackgroundJobModel.dedup_key.like(f"{_DIAGNOSTIC_JOB_PREFIX}%:{marker}"),
        )
        .order_by(BackgroundJobModel.created_at.desc())
        .limit(20)
    ).all()
    return [
        {
            "id": row.id,
            "job_type": row.job_type,
            "status": row.status,
            "attempts": row.attempts,
            "max_attempts": row.max_attempts,
            "run_at": row.run_at,
            "started_at": row.started_at,
            "finished_at": row.finished_at,
            "last_error": row.last_error,
        }
        for row in rows
    ]


@router.get("/operator/overview")
def operator_overview(
    _: OperatorReadUser,
    db: DatabaseDependency,
    container: ContainerDependency,
) -> dict[str, object]:
    stores = int(db.scalar(select(func.count(StoreModel.id))) or 0)
    connections = db.execute(
        select(ProviderConnectionModel.status, func.count(ProviderConnectionModel.id)).group_by(
            ProviderConnectionModel.status
        )
    ).all()
    subscriptions = db.execute(
        select(SubscriptionModel.status, func.count(SubscriptionModel.id)).group_by(
            SubscriptionModel.status
        )
    ).all()
    total_ai_cost = db.scalar(select(func.sum(AIUsageRecordModel.cost_numeric)))
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "stores": stores,
        "provider_health": {str(status): int(count) for status, count in connections},
        "subscriptions": {str(status): int(count) for status, count in subscriptions},
        "ai_cost": str(total_ai_cost or 0),
        "queue": container.job_queue.metrics(),
    }


@router.get("/operator/alerts")
def operator_alerts(
    _: OperatorReadUser,
    db: DatabaseDependency,
    container: ContainerDependency,
) -> dict[str, object]:
    """Return operator-facing alert state without payloads, errors, or secret values."""

    queue_metrics = container.job_queue.metrics()
    stale_running = container.job_queue.stale_running_count(
        stale_after_seconds=container.settings.worker_lease_seconds
    )
    provider_rows = db.execute(
        select(ProviderConnectionModel.status, func.count(ProviderConnectionModel.id))
        .where(ProviderConnectionModel.status.in_(_PROVIDER_ATTENTION_STATUSES))
        .group_by(ProviderConnectionModel.status)
    ).all()
    provider_counts = {str(status): int(count) for status, count in provider_rows}
    provider_attention = sum(provider_counts.values())
    alerts = [
        *_queue_alerts(queue_metrics, stale_running=stale_running),
        _operational_alert(
            code="provider_connections_attention",
            severity="warning",
            status="firing" if provider_attention > 0 else "ok",
            message=(
                "Provider connections need owner or operator attention."
                if provider_attention > 0
                else "No provider connections currently need attention."
            ),
            details={"connections": provider_counts},
        ),
        _configuration_alert(container.settings.production_readiness_issues()),
    ]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "alerts": alerts,
    }


@router.get("/operator/jobs")
def operator_jobs(
    _: OperatorReadUser,
    db: DatabaseDependency,
    status: Annotated[str, Query(pattern=r"^(pending|running|succeeded|dead)$")] = "dead",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[dict[str, object]]:
    rows = db.scalars(
        select(BackgroundJobModel)
        .where(BackgroundJobModel.status == status)
        .order_by(BackgroundJobModel.created_at.desc())
        .limit(limit)
    ).all()
    return [
        {
            "id": row.id,
            "store_id": row.store_id,
            "job_type": row.job_type,
            "status": row.status,
            "attempts": row.attempts,
            "max_attempts": row.max_attempts,
            "run_at": row.run_at,
            "last_error": row.last_error,
            "created_at": row.created_at,
            "finished_at": row.finished_at,
        }
        for row in rows
    ]


@router.post("/operator/jobs/{job_id}/replay")
def replay_job(
    job_id: int,
    user: OperatorUser,
    db: DatabaseDependency,
    container: ContainerDependency,
) -> dict[str, object]:
    if not container.job_queue.replay_dead_job(job_id):
        raise NotFoundError("Dead-lettered job was not found")
    db.add(
        AuditEventModel(
            actor=user.email,
            action="operator.job.replay",
            entity_type="background_job",
            entity_id=str(job_id),
            metadata_json={},
        )
    )
    return {"status": "queued", "job_id": job_id}


@router.get("/operator/audit")
def operator_audit(
    _: OperatorReadUser,
    db: DatabaseDependency,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[dict[str, object]]:
    rows = db.scalars(
        select(AuditEventModel).order_by(AuditEventModel.created_at.desc()).limit(limit)
    ).all()
    return [
        {
            "id": row.id,
            "actor": row.actor,
            "action": row.action,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "metadata": row.metadata_json,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@router.get("/operator/stores")
def operator_stores(
    _: OperatorReadUser,
    db: DatabaseDependency,
    query: Annotated[str, Query(max_length=160)] = "",
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[dict[str, object]]:
    statement = select(StoreModel).order_by(StoreModel.created_at.desc()).limit(limit)
    if query.strip():
        pattern = f"%{query.strip()}%"
        statement = statement.where(
            (StoreModel.name.ilike(pattern)) | (StoreModel.slug.ilike(pattern))
        )
    rows = db.scalars(statement).all()
    result: list[dict[str, object]] = []
    for store in rows:
        connections = db.execute(
            select(ProviderConnectionModel.provider, ProviderConnectionModel.status).where(
                ProviderConnectionModel.store_id == store.id
            )
        ).all()
        quotas = db.execute(
            select(UsageRecordModel.metric, UsageRecordModel.quantity).where(
                UsageRecordModel.store_id == store.id
            )
        ).all()
        subscription = db.scalar(
            select(SubscriptionModel).where(
                SubscriptionModel.organization_id == store.organization_id
            )
        )
        store_ai_cost = db.scalar(
            select(func.sum(AIUsageRecordModel.cost_numeric)).where(
                AIUsageRecordModel.store_id == store.id
            )
        )
        result.append(
            {
                "id": store.id,
                "name": store.name,
                "slug": store.slug,
                "organization_id": store.organization_id,
                "status": "active" if store.is_active else "suspended",
                "subscription": (
                    {
                        "plan": subscription.plan_key,
                        "status": subscription.status,
                        "provider": subscription.provider,
                    }
                    if subscription
                    else None
                ),
                "providers": [
                    {"provider": provider, "status": status} for provider, status in connections
                ],
                "quotas": {str(metric): int(quantity) for metric, quantity in quotas},
                "ai_cost": str(store_ai_cost or 0),
                "created_at": store.created_at,
            }
        )
    return result


@router.patch("/operator/stores/{store_id}/suspension")
def suspend_store(
    store_id: str,
    payload: StoreSuspensionInput,
    user: OperatorUser,
    db: DatabaseDependency,
) -> dict[str, object]:
    store = db.get(StoreModel, store_id)
    if store is None:
        raise NotFoundError(details={"entity": "store"})
    store.is_active = not payload.suspended
    db.add(
        AuditEventModel(
            organization_id=store.organization_id,
            store_id=store.id,
            actor_user_id=user.user_id,
            actor=user.email,
            action=(
                "operator.store.suspended" if payload.suspended else "operator.store.reactivated"
            ),
            entity_type="store",
            entity_id=store.id,
            metadata_json={"reason": payload.reason},
        )
    )
    return {
        "store_id": store.id,
        "status": "suspended" if payload.suspended else "active",
    }


@router.get("/operator/stores/{store_id}/diagnostics")
def store_diagnostics(
    store_id: str,
    _: OperatorReadUser,
    db: DatabaseDependency,
) -> dict[str, object]:
    store = db.get(StoreModel, store_id)
    if store is None:
        raise NotFoundError(details={"entity": "store"})
    connections = db.scalars(
        select(ProviderConnectionModel)
        .where(ProviderConnectionModel.store_id == store_id)
        .order_by(ProviderConnectionModel.provider)
    ).all()
    return {
        "store_id": store.id,
        "status": "active" if store.is_active else "suspended",
        "connections": [
            {
                "id": row.id,
                "provider": row.provider,
                "type": row.connection_type,
                "display_name": row.display_name,
                "external_account_id": row.external_account_id,
                "external_resource_id": row.external_resource_id,
                "status": row.status,
                "capabilities": row.capabilities_json,
                "token_expires_at": row.token_expires_at,
                "last_health_at": row.last_health_at,
                "last_successful_sync_at": row.last_successful_sync_at,
                "last_error_code": row.last_error_code,
                "action_required": row.status in {"degraded", "expired", "action_required"},
            }
            for row in connections
        ],
    }


@router.get("/operator/webhooks")
def operator_webhooks(
    _: OperatorReadUser,
    db: DatabaseDependency,
    store_id: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[dict[str, object]]:
    provider_statement = (
        select(ProviderWebhookEventModel)
        .order_by(ProviderWebhookEventModel.received_at.desc())
        .limit(limit)
    )
    if store_id:
        provider_statement = provider_statement.where(
            ProviderWebhookEventModel.store_id == store_id
        )
    provider_rows = db.scalars(provider_statement).all()
    result: list[dict[str, object]] = [
        {
            "source": "provider",
            "store_id": row.store_id,
            "provider": row.provider,
            "event_type": row.event_type,
            "event_id": row.external_event_id,
            "received_at": row.received_at,
        }
        for row in provider_rows
    ]
    if not store_id:
        stripe_rows = db.scalars(
            select(StripeEventModel).order_by(StripeEventModel.received_at.desc()).limit(limit)
        ).all()
        result.extend(
            {
                "source": "stripe",
                "store_id": None,
                "provider": "stripe",
                "event_type": row.event_type,
                "event_id": row.event_id,
                "received_at": row.received_at,
            }
            for row in stripe_rows
        )
    return sorted(
        result,
        key=lambda item: str(item["received_at"]),
        reverse=True,
    )[:limit]
