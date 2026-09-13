"""Database-backed fixed-window limits shared by all application instances."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import RateLimitBucketModel
from app.domain.errors import RateLimitedError


def _window_start(now: datetime, window_seconds: int) -> datetime:
    epoch = int(now.timestamp())
    return datetime.fromtimestamp(epoch - (epoch % window_seconds), tz=UTC)


def _cleanup_expired_buckets(session: Session, now: datetime, bucket_id: int) -> None:
    if bucket_id % 100 == 0:
        session.execute(delete(RateLimitBucketModel).where(RateLimitBucketModel.expires_at < now))


def enforce_rate_limit(
    session: Session,
    key: str,
    *,
    max_requests: int,
    window_seconds: int = 60,
) -> None:
    now = datetime.now(UTC)
    start = _window_start(now, 1)
    cutoff = now - timedelta(seconds=window_seconds)
    key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
    request_count = session.scalar(
        select(func.coalesce(func.sum(RateLimitBucketModel.request_count), 0)).where(
            RateLimitBucketModel.key_hash == key_hash,
            RateLimitBucketModel.window_start >= cutoff,
        )
    )
    if int(request_count or 0) >= max_requests:
        raise RateLimitedError(details={"retry_after_seconds": 1})
    statement = (
        select(RateLimitBucketModel)
        .where(
            RateLimitBucketModel.key_hash == key_hash,
            RateLimitBucketModel.window_start == start,
        )
        .with_for_update()
    )
    bucket = session.scalar(statement)
    if bucket is None:
        try:
            with session.begin_nested():
                bucket = RateLimitBucketModel(
                    key_hash=key_hash,
                    window_start=start,
                    request_count=1,
                    expires_at=now + timedelta(seconds=window_seconds * 2),
                )
                session.add(bucket)
                session.flush()
            _cleanup_expired_buckets(session, now, bucket.id)
            return
        except IntegrityError:
            bucket = session.scalar(statement)
    if bucket is None:
        raise RateLimitedError()
    bucket.request_count += 1
    _cleanup_expired_buckets(session, now, bucket.id)
    session.flush()


def enforce_persistent_rate_limit(
    factory: sessionmaker[Session],
    key: str,
    *,
    max_requests: int,
    window_seconds: int = 60,
) -> None:
    """Commit abuse counters independently from a request that may be rejected."""

    with factory.begin() as session:
        enforce_rate_limit(
            session,
            key,
            max_requests=max_requests,
            window_seconds=window_seconds,
        )
