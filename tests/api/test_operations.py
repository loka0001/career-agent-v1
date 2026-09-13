"""Internal scheduler and operator controls are authenticated and functional."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pydantic import SecretStr
from sqlalchemy import delete, select

from app.db.models import BackgroundJobModel, StoreModel
from app.services.job_queue import enqueue_job, job_handler
from tests.conftest import TEST_EMAIL, TestContext


@job_handler("test.cron.noop")
def _cron_noop(session, payload) -> None:
    del session, payload


def test_internal_job_drain_requires_constant_secret(context: TestContext) -> None:
    original = context.container.settings.cron_secret
    context.container.settings.cron_secret = SecretStr("c" * 48)
    try:
        rejected = context.client.get(
            "/api/v1/internal/jobs/drain",
            headers={"Authorization": "Bearer wrong"},
        )
        assert rejected.status_code == 401

        with context.session_factory.begin() as session:
            enqueue_job(
                session,
                job_type="test.cron.noop",
                dedup_key="test-cron-noop",
            )
        accepted = context.client.get(
            "/api/v1/internal/jobs/drain",
            headers={"Authorization": f"Bearer {'c' * 48}"},
        )
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()["status"] == "ok"
        assert accepted.json()["executed"] >= 1
    finally:
        context.container.settings.cron_secret = original


def test_internal_stale_recovery_does_not_execute_jobs(context: TestContext) -> None:
    original = context.container.settings.cron_secret
    context.container.settings.cron_secret = SecretStr("r" * 48)
    try:
        with context.session_factory.begin() as session:
            job = enqueue_job(
                session,
                job_type="test.cron.noop",
                dedup_key="test-recover-only",
            )
            assert job is not None
            job.status = "running"
            job.lease_token = "abandoned-lease"
            job.leased_until = datetime.now(UTC) - timedelta(minutes=1)

        rejected = context.client.post(
            "/api/v1/internal/jobs/recover-stale",
            headers={"Authorization": "Bearer wrong"},
        )
        assert rejected.status_code == 401

        assert context.client.get("/health/ready").status_code == 503
        accepted = context.client.post(
            "/api/v1/internal/jobs/recover-stale",
            headers={"Authorization": f"Bearer {'r' * 48}"},
        )
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()["status"] == "ok"
        assert accepted.json()["recovered"] == 1

        with context.session_factory.begin() as session:
            recovered = session.scalar(
                select(BackgroundJobModel).where(
                    BackgroundJobModel.dedup_key == "test-recover-only"
                )
            )
            assert recovered is not None
            assert recovered.status == "pending"
            assert recovered.attempts == 0
            assert recovered.last_error == "Recovered after worker termination"
        assert context.client.get("/health/ready").status_code == 200
        with context.session_factory.begin() as session:
            recovered = session.scalar(
                select(BackgroundJobModel).where(
                    BackgroundJobModel.dedup_key == "test-recover-only"
                )
            )
            assert recovered is not None
            session.delete(recovered)
    finally:
        context.container.settings.cron_secret = original


def test_internal_job_diagnostics_cover_duplicate_and_retry(context: TestContext) -> None:
    original = context.container.settings.cron_secret
    context.container.settings.cron_secret = SecretStr("d" * 48)
    headers = {"Authorization": f"Bearer {'d' * 48}"}
    try:
        queued = context.client.post(
            "/api/v1/internal/jobs/diagnostics",
            headers=headers,
            params={"scenario": "success", "marker": "diagnostic-test"},
        )
        assert queued.status_code == 200, queued.text
        assert queued.json()["status"] == "queued"

        duplicate = context.client.post(
            "/api/v1/internal/jobs/diagnostics",
            headers=headers,
            params={"scenario": "success", "marker": "diagnostic-test"},
        )
        assert duplicate.status_code == 200, duplicate.text
        assert duplicate.json()["status"] == "duplicate"

        retry = context.client.post(
            "/api/v1/internal/jobs/diagnostics",
            headers=headers,
            params={"scenario": "retry_once", "marker": "diagnostic-retry"},
        )
        assert retry.status_code == 200, retry.text

        first_drain = context.client.get(
            "/api/v1/internal/jobs/drain",
            headers=headers,
        )
        assert first_drain.status_code == 200, first_drain.text

        with context.session_factory.begin() as session:
            retry_row = session.scalar(
                select(BackgroundJobModel).where(
                    BackgroundJobModel.dedup_key
                    == "operations.diagnostic.retry_once:diagnostic-retry"
                )
            )
            assert retry_row is not None
            assert retry_row.status == "pending"
            assert retry_row.attempts == 1
            retry_row.run_at = datetime.now(UTC) - timedelta(seconds=1)

        second_drain = context.client.get(
            "/api/v1/internal/jobs/drain",
            headers=headers,
        )
        assert second_drain.status_code == 200, second_drain.text

        status = context.client.get(
            "/api/v1/internal/jobs/diagnostics",
            headers=headers,
            params={"marker": "diagnostic-retry"},
        )
        assert status.status_code == 200, status.text
        assert status.json()[0]["status"] == "succeeded"
        assert status.json()[0]["attempts"] == 2
    finally:
        context.container.settings.cron_secret = original


def test_operator_routes_fail_closed_then_allow_configured_operator(
    context: TestContext,
) -> None:
    headers = context.login()
    denied = context.client.get("/api/v1/operator/overview", headers=headers)
    assert denied.status_code == 403

    original = list(context.container.settings.operator_emails)
    context.container.settings.operator_emails = [TEST_EMAIL]
    try:
        with context.session_factory.begin() as session:
            session.execute(delete(BackgroundJobModel).where(BackgroundJobModel.status == "dead"))

        overview = context.client.get("/api/v1/operator/overview", headers=headers)
        assert overview.status_code == 200, overview.text
        assert "queue" in overview.json()
        alerts = context.client.get("/api/v1/operator/alerts", headers=headers)
        assert alerts.status_code == 200, alerts.text
        dead_alert = next(
            item for item in alerts.json()["alerts"] if item["code"] == "queue_dead_jobs"
        )
        assert dead_alert["status"] == "ok"

        with context.session_factory.begin() as session:
            dead_job = enqueue_job(
                session,
                job_type="test.cron.noop",
                dedup_key="operator-alert-dead-job",
                max_attempts=1,
            )
            assert dead_job is not None
            dead_job.status = "dead"
            dead_job.last_error = "sensitive implementation detail"

        firing_alerts = context.client.get("/api/v1/operator/alerts", headers=headers)
        assert firing_alerts.status_code == 200, firing_alerts.text
        firing_dead_alert = next(
            item for item in firing_alerts.json()["alerts"] if item["code"] == "queue_dead_jobs"
        )
        assert firing_dead_alert["status"] == "firing"
        assert firing_dead_alert["details"]["failed"] >= 1
        assert "sensitive implementation detail" not in firing_alerts.text

        original_env = context.container.settings.app_env
        original_sentry = context.container.settings.sentry_dsn
        original_release_sha = context.container.settings.release_sha
        context.container.settings.app_env = "production"
        context.container.settings.sentry_dsn = type(original_sentry)("")
        context.container.settings.release_sha = ""
        try:
            config_alerts = context.client.get("/api/v1/operator/alerts", headers=headers)
            assert config_alerts.status_code == 200, config_alerts.text
            config_alert = next(
                item
                for item in config_alerts.json()["alerts"]
                if item["code"] == "production_readiness_incomplete"
            )
            assert config_alert["status"] == "firing"
            assert "external_monitoring_missing" in config_alert["details"]["issues"]
            assert "release_sha_missing" in config_alert["details"]["issues"]
            assert "worker_runtime_missing" in config_alert["details"]["issues"]
            assert "runtime-only" not in config_alerts.text
        finally:
            context.container.settings.app_env = original_env
            context.container.settings.sentry_dsn = original_sentry
            context.container.settings.release_sha = original_release_sha

        replay_target = context.client.get("/api/v1/operator/jobs", headers=headers)
        assert replay_target.status_code == 200, replay_target.text
        created_job = next(
            item for item in replay_target.json() if item["job_type"] == "test.cron.noop"
        )
        replayed = context.client.post(
            f"/api/v1/operator/jobs/{created_job['id']}/replay",
            headers=headers,
        )
        assert replayed.status_code == 200, replayed.text
        assert context.container.job_queue.run_due_jobs() >= 1

        stores = context.client.get("/api/v1/operator/stores", headers=headers)
        assert stores.status_code == 200, stores.text
        assert any(item["id"] == "demo-store" for item in stores.json())

        with context.session_factory.begin() as session:
            session.add(
                StoreModel(
                    id="operator-suspend-target",
                    organization_id="org_demo",
                    slug="operator-suspend-target",
                    name="Operator Target",
                )
            )
        suspended = context.client.patch(
            "/api/v1/operator/stores/operator-suspend-target/suspension",
            headers=headers,
            json={"suspended": True, "reason": "Automated security test"},
        )
        assert suspended.status_code == 200, suspended.text
        diagnostics = context.client.get(
            "/api/v1/operator/stores/operator-suspend-target/diagnostics",
            headers=headers,
        )
        assert diagnostics.status_code == 200
        assert diagnostics.json()["status"] == "suspended"
        webhooks = context.client.get("/api/v1/operator/webhooks", headers=headers)
        assert webhooks.status_code == 200
    finally:
        context.container.settings.operator_emails = original
