"""Event-driven, idempotent automations with consent-safe actions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    AuditEventModel,
    AutomationModel,
    AutomationRunModel,
    ConversationModel,
    CustomerModel,
    StoreModel,
)
from app.domain.enums import (
    AutomationActionType,
    AutomationTrigger,
    MessageSenderType,
)
from app.domain.errors import ConflictError, NotFoundError
from app.domain.models import (
    AutomationAction,
    AutomationCondition,
    AutomationInput,
    AutomationOut,
    AutomationRunOut,
    DraftOrderInput,
    OrderItemInput,
)
from app.services.billing import check_resource_limit
from app.services.conversations import add_internal_note, queue_outbound_message
from app.services.job_queue import enqueue_job, job_handler
from app.services.opportunities import _add

AUTOMATION_TEMPLATES: dict[str, AutomationInput] = {
    "draft_new_message_reply": AutomationInput(
        name="مسودة رد لكل رسالة جديدة",
        trigger_type=AutomationTrigger.NEW_MESSAGE,
        actions=[
            AutomationAction(
                action_type=AutomationActionType.DRAFT_REPLY,
                config={"text": "راجع رسالة العميل واقترح ردًا مناسبًا."},
            )
        ],
    ),
    "abandoned_cart_followup": AutomationInput(
        name="متابعة السلة المتروكة",
        trigger_type=AutomationTrigger.ABANDONED_CART,
        actions=[
            AutomationAction(
                action_type=AutomationActionType.SEND_MESSAGE,
                config={"text": "منتجاتك ما زالت محفوظة. هل واجهتك مشكلة في إكمال الطلب؟"},
            )
        ],
        delay_seconds=3600,
        approval_required=True,
    ),
    "low_stock_alert": AutomationInput(
        name="تنبيه المخزون المنخفض",
        trigger_type=AutomationTrigger.LOW_STOCK,
        actions=[
            AutomationAction(
                action_type=AutomationActionType.RAISE_ALERT,
                config={"message": "منتج يحتاج مراجعة مخزون."},
            )
        ],
    ),
}


def _automation_out(row: AutomationModel) -> AutomationOut:
    return AutomationOut(
        id=row.id,
        name=row.name,
        trigger_type=AutomationTrigger(row.trigger_type),
        conditions=[AutomationCondition.model_validate(item) for item in row.conditions_json],
        actions=[AutomationAction.model_validate(item) for item in row.actions_json],
        delay_seconds=row.delay_seconds,
        approval_required=row.approval_required,
        is_enabled=row.is_enabled,
        template_key=row.template_key,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _run_out(row: AutomationRunModel) -> AutomationRunOut:
    return AutomationRunOut(
        id=row.id,
        automation_id=row.automation_id,
        event_key=row.event_key,
        event=dict(row.event_json),
        status=row.status,
        last_error=row.last_error,
        started_at=row.started_at,
        finished_at=row.finished_at,
        created_at=row.created_at,
    )


def create_automation(
    session: Session,
    store_id: str,
    payload: AutomationInput,
    *,
    template_key: str | None = None,
) -> AutomationOut:
    store = session.get(StoreModel, store_id)
    organization_id = store.organization_id if store is not None else None
    automation_count = session.scalar(
        select(func.count(AutomationModel.id))
        .join(StoreModel, StoreModel.id == AutomationModel.store_id)
        .where(StoreModel.organization_id == organization_id)
    )
    check_resource_limit(session, store_id, "automations", int(automation_count or 0))
    row = AutomationModel(
        store_id=store_id,
        name=payload.name,
        trigger_type=payload.trigger_type.value,
        conditions_json=[item.model_dump(mode="json") for item in payload.conditions],
        actions_json=[item.model_dump(mode="json") for item in payload.actions],
        delay_seconds=payload.delay_seconds,
        approval_required=payload.approval_required,
        is_enabled=payload.is_enabled,
        template_key=template_key,
    )
    session.add(row)
    session.flush()
    return _automation_out(row)


def list_automations(session: Session, store_id: str) -> list[AutomationOut]:
    rows = session.scalars(
        select(AutomationModel)
        .where(AutomationModel.store_id == store_id)
        .order_by(AutomationModel.created_at.desc())
    ).all()
    return [_automation_out(row) for row in rows]


def list_runs(
    session: Session, store_id: str, automation_id: int | None = None
) -> list[AutomationRunOut]:
    statement = (
        select(AutomationRunModel)
        .where(AutomationRunModel.store_id == store_id)
        .order_by(AutomationRunModel.created_at.desc())
        .limit(200)
    )
    if automation_id is not None:
        statement = statement.where(AutomationRunModel.automation_id == automation_id)
    return [_run_out(row) for row in session.scalars(statement).all()]


def _compare(actual: object, operator: str, expected: object) -> bool:
    if operator == "eq":
        return actual == expected
    if operator == "neq":
        return actual != expected
    if operator == "contains":
        return str(expected) in str(actual)
    if operator == "in":
        return isinstance(expected, list) and str(actual) in {str(item) for item in expected}
    try:
        left, right = float(str(actual)), float(str(expected))
    except ValueError:
        return False
    return {
        "gt": left > right,
        "gte": left >= right,
        "lt": left < right,
        "lte": left <= right,
    }.get(operator, False)


def _matches(conditions: list[dict[str, Any]], event: dict[str, Any]) -> bool:
    return all(
        _compare(
            event.get(str(condition["field"])),
            str(condition["operator"]),
            condition["value"],
        )
        for condition in conditions
    )


def dispatch_automation_event(
    session: Session,
    store_id: str,
    trigger: AutomationTrigger,
    event: dict[str, Any],
    event_key: str,
) -> int:
    automations = session.scalars(
        select(AutomationModel).where(
            AutomationModel.store_id == store_id,
            AutomationModel.trigger_type == trigger.value,
            AutomationModel.is_enabled.is_(True),
        )
    ).all()
    created = 0
    for automation in automations:
        if not _matches(automation.conditions_json, event):
            continue
        existing = session.scalar(
            select(AutomationRunModel.id).where(
                AutomationRunModel.automation_id == automation.id,
                AutomationRunModel.event_key == event_key,
            )
        )
        if existing is not None:
            continue
        run = AutomationRunModel(
            automation_id=automation.id,
            store_id=store_id,
            event_key=event_key,
            event_json=event,
            status=("awaiting_approval" if automation.approval_required else "pending"),
        )
        session.add(run)
        session.flush()
        if not automation.approval_required:
            enqueue_job(
                session,
                job_type="automation.execute",
                store_id=store_id,
                payload={"run_id": run.id},
                run_at=datetime.now(UTC) + timedelta(seconds=automation.delay_seconds),
                dedup_key=f"automation-run:{run.id}",
            )
        created += 1
    return created


def approve_run(session: Session, store_id: str, run_id: int) -> AutomationRunOut:
    run = session.scalar(
        select(AutomationRunModel).where(
            AutomationRunModel.id == run_id,
            AutomationRunModel.store_id == store_id,
        )
    )
    if run is None:
        raise NotFoundError(details={"entity": "automation_run", "id": run_id})
    if run.status != "awaiting_approval":
        raise ConflictError("Automation run is not awaiting approval")
    automation = session.get(AutomationModel, run.automation_id)
    if automation is None:
        raise NotFoundError(details={"entity": "automation"})
    run.status = "pending"
    enqueue_job(
        session,
        job_type="automation.execute",
        store_id=store_id,
        payload={"run_id": run.id},
        run_at=datetime.now(UTC) + timedelta(seconds=automation.delay_seconds),
        dedup_key=f"automation-run:{run.id}",
    )
    session.flush()
    return _run_out(run)


def set_enabled(
    session: Session, store_id: str, automation_id: int, enabled: bool
) -> AutomationOut:
    row = session.scalar(
        select(AutomationModel).where(
            AutomationModel.id == automation_id,
            AutomationModel.store_id == store_id,
        )
    )
    if row is None:
        raise NotFoundError(details={"entity": "automation", "id": automation_id})
    row.is_enabled = enabled
    session.flush()
    return _automation_out(row)


def install_template(session: Session, store_id: str, template_key: str) -> AutomationOut:
    template = AUTOMATION_TEMPLATES.get(template_key)
    if template is None:
        raise NotFoundError(details={"entity": "automation_template"})
    existing = session.scalar(
        select(AutomationModel).where(
            AutomationModel.store_id == store_id,
            AutomationModel.template_key == template_key,
        )
    )
    if existing is not None:
        return _automation_out(existing)
    return create_automation(session, store_id, template, template_key=template_key)


def _conversation(session: Session, store_id: str, event: dict[str, Any]) -> ConversationModel:
    conversation_id = int(str(event.get("conversation_id", 0)))
    row = session.scalar(
        select(ConversationModel).where(
            ConversationModel.id == conversation_id,
            ConversationModel.store_id == store_id,
        )
    )
    if row is None:
        raise NotFoundError(details={"entity": "conversation"})
    return row


def _execute_action(
    session: Session,
    run: AutomationRunModel,
    action: AutomationAction,
) -> None:
    event = dict(run.event_json)
    config = action.config
    if action.action_type == AutomationActionType.DRAFT_REPLY:
        add_internal_note(
            session,
            conversation=_conversation(session, run.store_id, event),
            text=f"[Automation draft] {config.get('text', '')}",
            sender_user_id=None,
        )
    elif action.action_type == AutomationActionType.SEND_MESSAGE:
        queue_outbound_message(
            session,
            store_id=run.store_id,
            conversation=_conversation(session, run.store_id, event),
            text=str(config.get("text", "")),
            sender_type=MessageSenderType.ASSISTANT,
        )
    elif action.action_type == AutomationActionType.ADD_TAG:
        customer_id = int(str(event.get("customer_id", 0)))
        customer = session.scalar(
            select(CustomerModel).where(
                CustomerModel.id == customer_id,
                CustomerModel.store_id == run.store_id,
            )
        )
        if customer is None:
            raise NotFoundError(details={"entity": "customer"})
        customer.tags_json = sorted(
            set(customer.tags_json) | {str(config.get("tag", "automation"))}
        )
    elif action.action_type == AutomationActionType.ASSIGN_TEAMMATE:
        _conversation(session, run.store_id, event).assignee_user_id = (
            str(config.get("user_id", "")) or None
        )
    elif action.action_type == AutomationActionType.CREATE_OPPORTUNITY:
        _add(
            session,
            store_id=run.store_id,
            opportunity_type=str(config.get("opportunity_type", "automation")),
            dedup_key=f"automation:{run.id}",
            reason=str(config.get("reason", "Created by automation")),
            expected_revenue=Decimal(str(config.get("expected_revenue", 0))),
            confidence=int(str(config.get("confidence", 70))),
            suggested_action=str(config.get("suggested_action", "Review")),
            message=str(config.get("message", "")),
            customer_id=(int(str(event["customer_id"])) if event.get("customer_id") else None),
        )
    elif action.action_type == AutomationActionType.CREATE_DRAFT_ORDER:
        from app.services.orders import create_draft_order

        product_id = str(config.get("product_id", event.get("product_id", "")))
        if not product_id:
            raise ConflictError("Automation draft order requires a product_id")
        create_draft_order(
            session,
            run.store_id,
            None,
            DraftOrderInput(
                conversation_id=_conversation(session, run.store_id, event).id,
                items=[
                    OrderItemInput(
                        product_id=product_id,
                        quantity=int(str(config.get("quantity", 1))),
                    )
                ],
                discount=Decimal(str(config.get("discount", 0))),
                notes=f"Created by automation run #{run.id}",
            ),
        )
    elif action.action_type == AutomationActionType.GENERATE_CONTENT:
        product_id = str(config.get("product_id", event.get("product_id", "")))
        if not product_id:
            raise ConflictError("Automation content generation requires a product_id")
        enqueue_job(
            session,
            job_type="content.generate_automation",
            store_id=run.store_id,
            payload={
                "run_id": run.id,
                "store_id": run.store_id,
                "product_id": product_id,
                "content_format": str(config.get("content_format", "sales_post")),
                "platform": str(config.get("platform", "facebook")),
                "tone": str(config.get("tone", "")),
            },
            dedup_key=f"automation-content:{run.id}",
        )
    elif action.action_type in {
        AutomationActionType.RAISE_ALERT,
        AutomationActionType.REQUEST_APPROVAL,
    }:
        session.add(
            AuditEventModel(
                actor="automation",
                action=action.action_type.value,
                entity_type="automation_run",
                entity_id=str(run.id),
                metadata_json={"event": event, "config": config},
            )
        )
    else:
        raise ConflictError(
            "Automation action needs additional order data",
            details={"action": action.action_type.value},
        )


@job_handler("automation.execute")
def execute_automation_job(session: Session, payload: dict[str, Any]) -> None:
    run = session.get(AutomationRunModel, int(payload["run_id"]))
    if run is None or run.status == "succeeded":
        return
    automation = session.get(AutomationModel, run.automation_id)
    if automation is None or not automation.is_enabled:
        run.status = "cancelled"
        run.finished_at = datetime.now(UTC)
        return
    run.status = "running"
    run.started_at = datetime.now(UTC)
    session.flush()
    try:
        for raw_action in automation.actions_json:
            _execute_action(session, run, AutomationAction.model_validate(raw_action))
    except Exception as exc:
        run.status = "failed"
        run.last_error = f"{type(exc).__name__}: {exc}"[:2000]
        session.commit()
        raise
    run.status = "succeeded"
    run.last_error = None
    run.finished_at = datetime.now(UTC)
