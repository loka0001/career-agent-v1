"""Durable provider-call ledger that prevents blind retries after ambiguous outcomes."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ExternalOperationModel

IN_FLIGHT = "in_flight"
SUCCEEDED = "succeeded"
RETRYABLE_FAILURE = "retryable_failure"
OUTCOME_UNKNOWN = "outcome_unknown"


@dataclass(frozen=True, slots=True)
class ExternalOperationDecision:
    should_execute: bool
    requires_reconciliation: bool
    attempt_id: str
    external_id: str | None = None


def _row(session: Session, store_id: str, operation_key: str) -> ExternalOperationModel:
    row = session.scalar(
        select(ExternalOperationModel)
        .where(
            ExternalOperationModel.store_id == store_id,
            ExternalOperationModel.operation_key == operation_key,
        )
        .with_for_update()
    )
    if row is None:
        raise LookupError(f"External operation '{operation_key}' does not exist")
    return row


def begin_external_operation(
    session: Session,
    *,
    store_id: str,
    operation_key: str,
    operation_type: str,
    entity_type: str,
    entity_id: str,
) -> ExternalOperationDecision:
    """Persist intent before a provider call and classify any unfinished prior attempt.

    The commit is deliberate: if the worker disappears after the provider accepts
    the request, a later lease observes ``in_flight`` and stops for reconciliation
    instead of automatically repeating the external side effect.
    """

    now = datetime.now(UTC)
    row = session.scalar(
        select(ExternalOperationModel)
        .where(
            ExternalOperationModel.store_id == store_id,
            ExternalOperationModel.operation_key == operation_key,
        )
        .with_for_update()
    )
    if row is None:
        row = ExternalOperationModel(
            store_id=store_id,
            operation_key=operation_key,
            operation_type=operation_type,
            entity_type=entity_type,
            entity_id=entity_id,
            status=IN_FLIGHT,
            attempt_id=uuid.uuid4().hex,
            attempts=1,
            started_at=now,
        )
        session.add(row)
        session.commit()
        return ExternalOperationDecision(True, False, row.attempt_id)

    if row.status == SUCCEEDED:
        return ExternalOperationDecision(False, False, row.attempt_id, row.external_id)
    if row.status in {IN_FLIGHT, OUTCOME_UNKNOWN}:
        row.status = OUTCOME_UNKNOWN
        row.last_error_code = "provider_outcome_unknown"
        row.completed_at = now
        session.commit()
        return ExternalOperationDecision(False, True, row.attempt_id, row.external_id)

    row.status = IN_FLIGHT
    row.attempt_id = uuid.uuid4().hex
    row.attempts += 1
    row.external_id = None
    row.last_error_code = None
    row.started_at = now
    row.completed_at = None
    session.commit()
    return ExternalOperationDecision(True, False, row.attempt_id)


def complete_external_operation(
    session: Session,
    store_id: str,
    operation_key: str,
    *,
    external_id: str | None,
) -> None:
    row = _row(session, store_id, operation_key)
    row.status = SUCCEEDED
    row.external_id = external_id
    row.last_error_code = None
    row.completed_at = datetime.now(UTC)


def mark_external_operation_retryable(
    session: Session,
    store_id: str,
    operation_key: str,
    error_code: str | None,
) -> None:
    row = _row(session, store_id, operation_key)
    row.status = RETRYABLE_FAILURE
    row.last_error_code = (error_code or "provider_rejected")[:100]
    row.completed_at = datetime.now(UTC)


def mark_external_operation_unknown(
    session: Session,
    store_id: str,
    operation_key: str,
) -> ExternalOperationModel:
    row = _row(session, store_id, operation_key)
    row.status = OUTCOME_UNKNOWN
    row.last_error_code = "provider_outcome_unknown"
    row.completed_at = datetime.now(UTC)
    return row
