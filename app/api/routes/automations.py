"""Automation definitions, templates, event dispatch, and run approvals."""

from fastapi import APIRouter

from app.api.dependencies import AdminUser, CurrentUser, DatabaseDependency
from app.domain.models import (
    AutomationEventInput,
    AutomationInput,
    AutomationOut,
    AutomationRunOut,
)
from app.services.automations import (
    AUTOMATION_TEMPLATES,
    approve_run,
    create_automation,
    dispatch_automation_event,
    install_template,
    list_automations,
    list_runs,
    set_enabled,
)
from app.services.billing import require_feature

router = APIRouter(prefix="/automations", tags=["automations"])


@router.get("", response_model=list[AutomationOut])
def automations(user: CurrentUser, db: DatabaseDependency) -> list[AutomationOut]:
    require_feature(db, user.store_id, "automations")
    return list_automations(db, user.store_id)


@router.post("", response_model=AutomationOut, status_code=201)
def add_automation(
    payload: AutomationInput, user: AdminUser, db: DatabaseDependency
) -> AutomationOut:
    require_feature(db, user.store_id, "automations")
    return create_automation(db, user.store_id, payload)


@router.get("/runs", response_model=list[AutomationRunOut])
def runs(
    user: CurrentUser,
    db: DatabaseDependency,
    automation_id: int | None = None,
) -> list[AutomationRunOut]:
    require_feature(db, user.store_id, "automations")
    return list_runs(db, user.store_id, automation_id)


@router.get("/templates")
def templates(user: CurrentUser, db: DatabaseDependency) -> list[dict[str, str]]:
    require_feature(db, user.store_id, "automations")
    return [
        {"key": key, "name": template.name}
        for key, template in AUTOMATION_TEMPLATES.items()
    ]


@router.post("/templates/{template_key}", response_model=AutomationOut)
def add_template(
    template_key: str, user: AdminUser, db: DatabaseDependency
) -> AutomationOut:
    require_feature(db, user.store_id, "automations")
    return install_template(db, user.store_id, template_key)


@router.post("/events")
def emit_event(
    payload: AutomationEventInput,
    user: AdminUser,
    db: DatabaseDependency,
) -> dict[str, int]:
    require_feature(db, user.store_id, "automations")
    created = dispatch_automation_event(
        db,
        user.store_id,
        payload.trigger_type,
        dict(payload.event),
        payload.event_key,
    )
    return {"runs_created": created}


@router.post("/runs/{run_id}/approve", response_model=AutomationRunOut)
def approve(
    run_id: int, user: AdminUser, db: DatabaseDependency
) -> AutomationRunOut:
    require_feature(db, user.store_id, "automations")
    return approve_run(db, user.store_id, run_id)


@router.post("/{automation_id}/enable", response_model=AutomationOut)
def enable(
    automation_id: int, user: AdminUser, db: DatabaseDependency
) -> AutomationOut:
    require_feature(db, user.store_id, "automations")
    return set_enabled(db, user.store_id, automation_id, True)


@router.post("/{automation_id}/disable", response_model=AutomationOut)
def disable(
    automation_id: int, user: AdminUser, db: DatabaseDependency
) -> AutomationOut:
    require_feature(db, user.store_id, "automations")
    return set_enabled(db, user.store_id, automation_id, False)
