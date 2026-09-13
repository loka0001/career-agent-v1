"""Generated automations slice of models.py."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.domain.enums import AutomationActionType, AutomationTrigger
from app.domain.model_groups.shared import ContractModel


class AutomationCondition(ContractModel):
    field: str = Field(min_length=1, max_length=100)
    operator: str = Field(pattern=r"^(eq|neq|gt|gte|lt|lte|contains|in)$")
    value: str | int | float | bool | list[str]


class AutomationAction(ContractModel):
    action_type: AutomationActionType
    config: dict[str, str | int | float | bool | list[str]] = Field(default_factory=dict)


class AutomationInput(ContractModel):
    name: str = Field(min_length=1, max_length=160)
    trigger_type: AutomationTrigger
    conditions: list[AutomationCondition] = Field(default_factory=list, max_length=20)
    actions: list[AutomationAction] = Field(min_length=1, max_length=20)
    delay_seconds: int = Field(default=0, ge=0, le=2_592_000)
    approval_required: bool = False
    is_enabled: bool = True


class AutomationOut(ContractModel):
    id: int
    name: str
    trigger_type: AutomationTrigger
    conditions: list[AutomationCondition]
    actions: list[AutomationAction]
    delay_seconds: int
    approval_required: bool
    is_enabled: bool
    template_key: str | None = None
    created_at: datetime
    updated_at: datetime


class AutomationRunOut(ContractModel):
    id: int
    automation_id: int
    event_key: str
    event: dict[str, Any]
    status: str
    last_error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime


class AutomationEventInput(ContractModel):
    trigger_type: AutomationTrigger
    event_key: str = Field(min_length=1, max_length=180)
    event: dict[str, str | int | float | bool] = Field(default_factory=dict)
