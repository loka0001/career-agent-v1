"""Durable guards for ambiguous external-provider outcomes."""

from __future__ import annotations

from sqlalchemy import select

from app.db.models import ExternalOperationModel
from app.services.external_operations import (
    OUTCOME_UNKNOWN,
    RETRYABLE_FAILURE,
    SUCCEEDED,
    begin_external_operation,
    complete_external_operation,
    mark_external_operation_retryable,
)
from tests.conftest import TestContext


def test_unfinished_external_call_requires_reconciliation_instead_of_resend(
    context: TestContext,
) -> None:
    with context.session_factory() as session:
        first = begin_external_operation(
            session,
            store_id="demo-store",
            operation_key="message:101",
            operation_type="channel.send_message",
            entity_type="message",
            entity_id="101",
        )
        assert first.should_execute is True
        assert first.attempt_id

    # Simulate a worker disappearing after the pre-call commit and before it can
    # persist the provider response. A retry must not invoke the provider again.
    with context.session_factory() as session:
        retry = begin_external_operation(
            session,
            store_id="demo-store",
            operation_key="message:101",
            operation_type="channel.send_message",
            entity_type="message",
            entity_id="101",
        )
        assert retry.should_execute is False
        assert retry.requires_reconciliation is True
        assert retry.attempt_id == first.attempt_id

    with context.session_factory() as session:
        row = session.scalar(
            select(ExternalOperationModel).where(
                ExternalOperationModel.operation_key == "message:101"
            )
        )
        assert row is not None
        assert row.status == OUTCOME_UNKNOWN
        assert row.attempts == 1
        assert row.last_error_code == "provider_outcome_unknown"


def test_explicit_failure_can_retry_with_a_new_attempt_identifier(context: TestContext) -> None:
    with context.session_factory() as session:
        first = begin_external_operation(
            session,
            store_id="demo-store",
            operation_key="message:102",
            operation_type="channel.send_message",
            entity_type="message",
            entity_id="102",
        )
        mark_external_operation_retryable(session, "demo-store", "message:102", "http_503")
        session.commit()

    with context.session_factory() as session:
        row = session.scalar(
            select(ExternalOperationModel).where(
                ExternalOperationModel.operation_key == "message:102"
            )
        )
        assert row is not None and row.status == RETRYABLE_FAILURE

        retry = begin_external_operation(
            session,
            store_id="demo-store",
            operation_key="message:102",
            operation_type="channel.send_message",
            entity_type="message",
            entity_id="102",
        )
        assert retry.should_execute is True
        assert retry.attempt_id != first.attempt_id
        assert row.attempts == 2


def test_completed_external_call_is_reused_without_resend(context: TestContext) -> None:
    with context.session_factory() as session:
        begin_external_operation(
            session,
            store_id="demo-store",
            operation_key="content:7:2",
            operation_type="content.publish",
            entity_type="content_item",
            entity_id="7",
        )
        complete_external_operation(
            session,
            "demo-store",
            "content:7:2",
            external_id="provider-post-77",
        )
        session.commit()

    with context.session_factory() as session:
        replay = begin_external_operation(
            session,
            store_id="demo-store",
            operation_key="content:7:2",
            operation_type="content.publish",
            entity_type="content_item",
            entity_id="7",
        )
        assert replay.should_execute is False
        assert replay.requires_reconciliation is False
        assert replay.external_id == "provider-post-77"

        row = session.scalar(
            select(ExternalOperationModel).where(
                ExternalOperationModel.operation_key == "content:7:2"
            )
        )
        assert row is not None
        assert row.status == SUCCEEDED
        assert row.attempts == 1
