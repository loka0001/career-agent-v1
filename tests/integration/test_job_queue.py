"""Background job queue behavior: execution, retry/backoff, dead-letter, dedup."""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import BackgroundJobModel
from app.services.job_queue import (
    JOB_STATUS_DEAD,
    JOB_STATUS_PENDING,
    JOB_STATUS_SUCCEEDED,
    JobQueue,
    JobWorker,
    enqueue_job,
)
from tests.conftest import TestContext


@pytest.fixture(autouse=True)
def isolate_job_queue(context: TestContext) -> None:
    with context.session_factory.begin() as session:
        session.execute(delete(BackgroundJobModel))


def test_job_executes_and_succeeds(context: TestContext) -> None:
    calls: list[dict[str, Any]] = []

    def handler(session: Session, payload: dict[str, Any]) -> None:
        del session
        calls.append(payload)

    queue = JobQueue(context.session_factory, handlers={"test.echo": handler})
    with context.session_factory.begin() as session:
        job = enqueue_job(session, job_type="test.echo", payload={"value": 7})
        assert job is not None
        job_id = job.id
    assert queue.run_due_jobs() == 1
    assert calls == [{"value": 7}]
    with context.session_factory() as session:
        stored = session.get(BackgroundJobModel, job_id)
        assert stored is not None
        assert stored.status == JOB_STATUS_SUCCEEDED
        assert stored.finished_at is not None
        assert stored.lease_token is None
        assert stored.leased_until is None


def test_failing_job_retries_then_dead_letters(context: TestContext) -> None:
    def handler(session: Session, payload: dict[str, Any]) -> None:
        del session, payload
        raise RuntimeError("boom")

    queue = JobQueue(context.session_factory, handlers={"test.fail": handler})
    with context.session_factory.begin() as session:
        job = enqueue_job(session, job_type="test.fail", max_attempts=2)
        assert job is not None
        job_id = job.id

    assert queue.run_due_jobs() == 1
    with context.session_factory.begin() as session:
        stored = session.get(BackgroundJobModel, job_id)
        assert stored is not None
        assert stored.status == JOB_STATUS_PENDING
        assert stored.attempts == 1
        assert stored.last_error is not None and "boom" in stored.last_error
        assert stored.run_at.replace(tzinfo=UTC) > datetime.now(UTC)
        stored.run_at = datetime.now(UTC) - timedelta(seconds=1)

    assert queue.run_due_jobs() == 1
    with context.session_factory() as session:
        stored = session.get(BackgroundJobModel, job_id)
        assert stored is not None
        assert stored.status == JOB_STATUS_DEAD
        assert stored.attempts == 2


def test_unknown_job_type_dead_letters(context: TestContext) -> None:
    queue = JobQueue(context.session_factory, handlers={})
    with context.session_factory.begin() as session:
        job = enqueue_job(session, job_type="test.unknown", max_attempts=1)
        assert job is not None
        job_id = job.id
    queue.run_due_jobs()
    with context.session_factory() as session:
        stored = session.get(BackgroundJobModel, job_id)
        assert stored is not None
        assert stored.status == JOB_STATUS_DEAD
        assert "No handler" in (stored.last_error or "")


def test_dedup_key_prevents_duplicates_and_future_jobs_wait(context: TestContext) -> None:
    with context.session_factory.begin() as session:
        first = enqueue_job(session, job_type="test.dedup", dedup_key="only-once", payload={"n": 1})
        duplicate = enqueue_job(
            session, job_type="test.dedup", dedup_key="only-once", payload={"n": 2}
        )
        future = enqueue_job(
            session,
            job_type="test.future",
            run_at=datetime.now(UTC) + timedelta(hours=1),
        )
        assert first is not None
        assert duplicate is None
        assert future is not None
    with context.session_factory() as session:
        count = len(
            session.scalars(
                select(BackgroundJobModel).where(BackgroundJobModel.dedup_key == "only-once")
            ).all()
        )
        assert count == 1

    executed: list[int] = []
    queue = JobQueue(
        context.session_factory,
        handlers={
            "test.dedup": lambda s, p: executed.append(1),
            "test.future": lambda s, p: executed.append(2),
        },
    )
    queue.run_due_jobs()
    assert executed == [1]


def test_stale_running_job_is_recovered(context: TestContext) -> None:
    queue = JobQueue(context.session_factory, handlers={"test.recover": lambda s, p: None})
    with context.session_factory.begin() as session:
        job = enqueue_job(session, job_type="test.recover")
        assert job is not None
        job.status = "running"
        job.updated_at = datetime.now(UTC) - timedelta(minutes=10)
        job.lease_token = "abandoned-lease"
        job.leased_until = datetime.now(UTC) - timedelta(seconds=1)
        job_id = job.id
    assert queue.stale_running_count(stale_after_seconds=60) == 1
    assert queue.recover_stale_jobs(stale_after_seconds=60) == 1
    assert queue.stale_running_count(stale_after_seconds=60) == 0
    assert queue.run_due_jobs() == 1
    with context.session_factory() as session:
        stored = session.get(BackgroundJobModel, job_id)
        assert stored is not None
        assert stored.status == JOB_STATUS_SUCCEEDED


def test_dead_job_can_be_replayed_and_queue_metrics_are_safe(context: TestContext) -> None:
    queue = JobQueue(context.session_factory, handlers={"test.replay": lambda s, p: None})
    with context.session_factory.begin() as session:
        job = enqueue_job(session, job_type="test.replay")
        assert job is not None
        job.status = JOB_STATUS_DEAD
        job.attempts = 3
        job.last_error = "provider token redacted"
        job.finished_at = datetime.now(UTC)
        job_id = job.id

    assert queue.replay_dead_job(job_id) is True
    assert queue.run_due_jobs() == 1
    metrics = queue.metrics()
    assert set(metrics) == {
        "queued",
        "running",
        "succeeded",
        "failed",
        "oldest_job_age_seconds",
    }
    assert metrics["succeeded"] >= 1
    with context.session_factory() as session:
        stored = session.get(BackgroundJobModel, job_id)
        assert stored is not None
        assert stored.status == JOB_STATUS_SUCCEEDED
        assert stored.attempts == 1


def test_concurrent_workers_claim_each_job_once(context: TestContext) -> None:
    calls: list[int] = []
    calls_lock = threading.Lock()

    def handler(session: Session, payload: dict[str, Any]) -> None:
        del session
        with calls_lock:
            calls.append(int(payload["value"]))

    queue = JobQueue(context.session_factory, handlers={"test.concurrent": handler})
    with context.session_factory.begin() as session:
        for value in range(8):
            enqueue_job(
                session,
                job_type="test.concurrent",
                payload={"value": value},
                dedup_key=f"test-concurrent-{value}",
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: queue.run_due_jobs(limit=8), range(2)))

    assert sum(results) == 8
    assert sorted(calls) == list(range(8))


def test_worker_health_tracks_successful_poll_freshness(context: TestContext) -> None:
    queue = JobQueue(context.session_factory, handlers={})
    worker = JobWorker(queue, poll_seconds=0.01)
    assert worker.health(readiness_window_seconds=1)["ready"] is False

    worker.start()
    try:
        for _ in range(50):
            health = worker.health(readiness_window_seconds=1)
            if health["ready"]:
                break
            time.sleep(0.01)
        assert health["status"] == "ok"
        assert health["last_successful_poll_at"] is not None
        assert health["last_error_code"] is None
        assert worker.health(readiness_window_seconds=0)["ready"] is False
    finally:
        worker.stop()


def test_worker_health_redacts_raw_iteration_errors() -> None:
    class FailingQueue:
        def recover_stale_jobs(self) -> int:
            return 0

        def run_due_jobs(self, *, limit: int = 10) -> int:
            del limit
            raise RuntimeError("secret-token-value")

        def metrics(self) -> dict[str, int | float | None]:
            return {
                "queued": 0,
                "running": 0,
                "succeeded": 0,
                "failed": 0,
                "oldest_job_age_seconds": None,
            }

    worker = JobWorker(FailingQueue(), poll_seconds=0.01)  # type: ignore[arg-type]
    worker.start()
    try:
        for _ in range(50):
            health = worker.health(readiness_window_seconds=1)
            if health["last_error_code"] is not None:
                break
            time.sleep(0.01)
        assert health["status"] == "degraded"
        assert health["last_error_code"] == "RuntimeError"
        assert "secret-token-value" not in str(health)
    finally:
        worker.stop()
