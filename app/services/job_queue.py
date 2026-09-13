"""DB-backed background job queue: retry with backoff, dead-letter, worker thread.

External or long-running work (channel sends, publishing, scans) must run here,
never inside an HTTP request. Handlers receive a fresh session and the payload;
they must be idempotent because a crashed run may execute twice.
"""

from __future__ import annotations

import logging
import secrets
import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import BackgroundJobModel

logger = logging.getLogger(__name__)

JobHandler = Callable[[Session, dict[str, Any]], None]

JOB_STATUS_PENDING = "pending"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_SUCCEEDED = "succeeded"
JOB_STATUS_DEAD = "dead"

RETRY_BASE_SECONDS = 30.0

_REGISTRY: dict[str, JobHandler] = {}


def job_handler(job_type: str) -> Callable[[JobHandler], JobHandler]:
    """Register a handler for a job type at import time."""

    def decorator(handler: JobHandler) -> JobHandler:
        _REGISTRY[job_type] = handler
        return handler

    return decorator


def registered_handlers() -> dict[str, JobHandler]:
    return dict(_REGISTRY)


def enqueue_job(
    session: Session,
    *,
    job_type: str,
    payload: dict[str, Any] | None = None,
    store_id: str | None = None,
    run_at: datetime | None = None,
    max_attempts: int = 3,
    dedup_key: str | None = None,
) -> BackgroundJobModel | None:
    """Queue a job; returns None when an identical dedup_key is already queued."""

    if dedup_key is not None:
        existing = session.scalar(
            select(BackgroundJobModel).where(BackgroundJobModel.dedup_key == dedup_key)
        )
        if existing is not None:
            return None
    job = BackgroundJobModel(
        store_id=store_id,
        job_type=job_type,
        payload_json=payload or {},
        run_at=run_at or datetime.now(UTC),
        max_attempts=max_attempts,
        dedup_key=dedup_key,
    )
    session.add(job)
    session.flush()
    return job


class JobQueue:
    """Claims due jobs and executes registered handlers with retry semantics."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        handlers: dict[str, JobHandler] | None = None,
        *,
        lease_seconds: int = 300,
    ):
        self._session_factory = session_factory
        self._handlers = handlers if handlers is not None else _REGISTRY
        self._lease_seconds = lease_seconds

    def run_due_jobs(self, *, limit: int = 10) -> int:
        """Execute up to `limit` due jobs; returns the number picked up."""

        executed = 0
        for _ in range(limit):
            claim = self._claim_one()
            if claim is None:
                break
            self._execute(*claim)
            executed += 1
        return executed

    def recover_stale_jobs(self, *, stale_after_seconds: int = 300) -> int:
        """Return jobs abandoned by a terminated worker to the retry queue."""

        now = datetime.now(UTC)
        cutoff = now - timedelta(seconds=stale_after_seconds)
        with self._session_factory.begin() as session:
            jobs = session.scalars(
                select(BackgroundJobModel)
                .where(
                    BackgroundJobModel.status == JOB_STATUS_RUNNING,
                    (
                        (BackgroundJobModel.leased_until.is_not(None))
                        & (BackgroundJobModel.leased_until < now)
                    )
                    | (
                        (BackgroundJobModel.leased_until.is_(None))
                        & (BackgroundJobModel.updated_at < cutoff)
                    ),
                )
                .with_for_update(skip_locked=True)
            ).all()
            for job in jobs:
                job.status = JOB_STATUS_PENDING
                job.run_at = now
                job.last_error = "Recovered after worker termination"
                job.lease_token = None
                job.leased_until = None
                job.heartbeat_at = None
            return len(jobs)

    def stale_running_count(self, *, stale_after_seconds: int = 300) -> int:
        """Count abandoned running jobs using the same lease policy as recovery."""

        now = datetime.now(UTC)
        cutoff = now - timedelta(seconds=stale_after_seconds)
        with self._session_factory() as session:
            count = session.scalar(
                select(func.count(BackgroundJobModel.id)).where(
                    BackgroundJobModel.status == JOB_STATUS_RUNNING,
                    (
                        (BackgroundJobModel.leased_until.is_not(None))
                        & (BackgroundJobModel.leased_until < now)
                    )
                    | (
                        (BackgroundJobModel.leased_until.is_(None))
                        & (BackgroundJobModel.updated_at < cutoff)
                    ),
                )
            )
        return int(count or 0)

    def metrics(self, *, store_id: str | None = None) -> dict[str, int | float | None]:
        """Return queue health without exposing payloads or errors."""

        now = datetime.now(UTC)
        with self._session_factory() as session:
            base = select(BackgroundJobModel)
            if store_id is not None:
                base = base.where(BackgroundJobModel.store_id == store_id)
            rows = session.scalars(base).all()
        counts = {
            status: sum(1 for row in rows if row.status == status)
            for status in (
                JOB_STATUS_PENDING,
                JOB_STATUS_RUNNING,
                JOB_STATUS_SUCCEEDED,
                JOB_STATUS_DEAD,
            )
        }
        pending_dates = [
            (
                row.created_at
                if row.created_at.tzinfo is not None
                else row.created_at.replace(tzinfo=UTC)
            )
            for row in rows
            if row.status == JOB_STATUS_PENDING
        ]
        oldest_age = max(0.0, (now - min(pending_dates)).total_seconds()) if pending_dates else None
        return {
            "queued": counts[JOB_STATUS_PENDING],
            "running": counts[JOB_STATUS_RUNNING],
            "succeeded": counts[JOB_STATUS_SUCCEEDED],
            "failed": counts[JOB_STATUS_DEAD],
            "oldest_job_age_seconds": oldest_age,
        }

    def replay_dead_job(
        self,
        job_id: int,
        *,
        store_id: str | None = None,
    ) -> bool:
        """Replay a dead-lettered job while preserving its idempotency key."""

        with self._session_factory.begin() as session:
            query = (
                select(BackgroundJobModel)
                .where(
                    BackgroundJobModel.id == job_id,
                    BackgroundJobModel.status == JOB_STATUS_DEAD,
                )
                .with_for_update()
            )
            if store_id is not None:
                query = query.where(BackgroundJobModel.store_id == store_id)
            job = session.scalar(query)
            if job is None:
                return False
            job.status = JOB_STATUS_PENDING
            job.attempts = 0
            job.run_at = datetime.now(UTC)
            job.last_error = None
            job.finished_at = None
            job.lease_token = None
            job.leased_until = None
            job.heartbeat_at = None
            job.started_at = None
            return True

    def _claim_one(self) -> tuple[int, str] | None:
        now = datetime.now(UTC)
        lease_token = secrets.token_hex(24)
        with self._session_factory.begin() as session:
            candidate = (
                select(BackgroundJobModel)
                .where(
                    BackgroundJobModel.status == JOB_STATUS_PENDING,
                    BackgroundJobModel.run_at <= now,
                )
                .order_by(BackgroundJobModel.run_at, BackgroundJobModel.id)
                .limit(1)
                .with_for_update(skip_locked=True)
                .with_only_columns(BackgroundJobModel.id)
                .scalar_subquery()
            )
            job_id = session.scalar(
                update(BackgroundJobModel)
                .where(
                    BackgroundJobModel.id == candidate,
                    BackgroundJobModel.status == JOB_STATUS_PENDING,
                )
                .values(
                    status=JOB_STATUS_RUNNING,
                    attempts=BackgroundJobModel.attempts + 1,
                    lease_token=lease_token,
                    leased_until=now + timedelta(seconds=self._lease_seconds),
                    heartbeat_at=now,
                    started_at=func.coalesce(BackgroundJobModel.started_at, now),
                    updated_at=now,
                )
                .returning(BackgroundJobModel.id)
            )
            if job_id is None:
                return None
            return job_id, lease_token

    def _execute(self, job_id: int, lease_token: str) -> None:
        error: str | None = None
        stop_heartbeat = threading.Event()
        heartbeat = threading.Thread(
            target=self._heartbeat_loop,
            args=(job_id, lease_token, stop_heartbeat),
            name=f"job-heartbeat-{job_id}",
            daemon=True,
        )
        heartbeat.start()
        with self._session_factory() as session:
            job = session.scalar(
                select(BackgroundJobModel).where(
                    BackgroundJobModel.id == job_id,
                    BackgroundJobModel.lease_token == lease_token,
                    BackgroundJobModel.status == JOB_STATUS_RUNNING,
                )
            )
            if job is None:
                stop_heartbeat.set()
                heartbeat.join(timeout=2)
                return
            handler = self._handlers.get(job.job_type)
            try:
                if handler is None:
                    raise LookupError(f"No handler registered for job type '{job.job_type}'")
                handler(session, dict(job.payload_json))
                job.status = JOB_STATUS_SUCCEEDED
                job.finished_at = datetime.now(UTC)
                job.last_error = None
                job.lease_token = None
                job.leased_until = None
                job.heartbeat_at = None
                session.commit()
            except Exception as exc:
                session.rollback()
                error = f"{type(exc).__name__}: {exc}"
        stop_heartbeat.set()
        heartbeat.join(timeout=2)
        if error is not None:
            self._record_failure(job_id, lease_token, error)

    def _heartbeat_loop(
        self,
        job_id: int,
        lease_token: str,
        stop: threading.Event,
    ) -> None:
        interval = max(5.0, self._lease_seconds / 3)
        while not stop.wait(interval):
            now = datetime.now(UTC)
            try:
                with self._session_factory.begin() as session:
                    job = session.scalar(
                        select(BackgroundJobModel).where(
                            BackgroundJobModel.id == job_id,
                            BackgroundJobModel.lease_token == lease_token,
                            BackgroundJobModel.status == JOB_STATUS_RUNNING,
                        )
                    )
                    if job is None:
                        return
                    job.heartbeat_at = now
                    job.leased_until = now + timedelta(seconds=self._lease_seconds)
            except Exception:
                logger.exception("job_heartbeat_failed", extra={"job_id": job_id})

    def _record_failure(self, job_id: int, lease_token: str, error: str) -> None:
        with self._session_factory.begin() as session:
            job = session.scalar(
                select(BackgroundJobModel).where(
                    BackgroundJobModel.id == job_id,
                    BackgroundJobModel.lease_token == lease_token,
                )
            )
            if job is None:
                return
            job.last_error = error[:2000]
            job.lease_token = None
            job.leased_until = None
            job.heartbeat_at = None
            if job.attempts >= job.max_attempts:
                job.status = JOB_STATUS_DEAD
                job.finished_at = datetime.now(UTC)
                logger.error(
                    "job_dead_lettered",
                    extra={"job_id": job.id, "job_type": job.job_type, "attempts": job.attempts},
                )
            else:
                job.status = JOB_STATUS_PENDING
                delay = RETRY_BASE_SECONDS * (2 ** (job.attempts - 1))
                job.run_at = datetime.now(UTC) + timedelta(seconds=delay)
                logger.warning(
                    "job_retry_scheduled",
                    extra={"job_id": job.id, "job_type": job.job_type, "delay_seconds": delay},
                )


class JobWorker:
    """Blocking queue worker with graceful shutdown support."""

    def __init__(self, queue: JobQueue, *, poll_seconds: float = 2.0):
        self._queue = queue
        self._poll_seconds = poll_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._started_at: datetime | None = None
        self._last_poll_at: datetime | None = None
        self._last_successful_poll_at: datetime | None = None
        self._last_error: str | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        recovered = self._queue.recover_stale_jobs()
        if recovered:
            logger.warning("stale_jobs_recovered", extra={"count": recovered})
        self._thread = threading.Thread(target=self._loop, name="job-worker", daemon=True)
        self._started_at = datetime.now(UTC)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def run_forever(self) -> None:
        """Run in the current process until ``stop`` is requested."""

        self._started_at = datetime.now(UTC)
        recovered = self._queue.recover_stale_jobs()
        if recovered:
            logger.warning("stale_jobs_recovered", extra={"count": recovered})
        self._loop()

    def health(self, *, readiness_window_seconds: float | None = None) -> dict[str, object]:
        window = (
            readiness_window_seconds
            if readiness_window_seconds is not None
            else max(30.0, self._poll_seconds * 3)
        )
        now = datetime.now(UTC)
        last_success = self._last_successful_poll_at
        stale = (
            last_success is None
            or (now - last_success.replace(tzinfo=UTC)).total_seconds() > window
        )
        ready = self._last_error is None and not stale
        return {
            "status": "ok" if ready else "degraded",
            "ready": ready,
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "last_poll_at": self._last_poll_at.isoformat() if self._last_poll_at else None,
            "last_successful_poll_at": (
                self._last_successful_poll_at.isoformat() if self._last_successful_poll_at else None
            ),
            "last_error_code": self._last_error,
            "readiness_window_seconds": window,
            "queue": self._queue.metrics(),
        }

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                picked = self._queue.run_due_jobs(limit=20)
                self._last_error = None
                self._last_successful_poll_at = datetime.now(UTC)
            except Exception as exc:
                logger.exception("job_worker_iteration_failed")
                self._last_error = type(exc).__name__
                picked = 0
            self._last_poll_at = datetime.now(UTC)
            if picked == 0:
                self._stop.wait(self._poll_seconds)
