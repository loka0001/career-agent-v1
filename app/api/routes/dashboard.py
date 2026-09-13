"""Merchant overview statistics endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.dependencies import CurrentUser, DatabaseDependency
from app.domain.models import DashboardSnapshot
from app.repositories.dashboard_repository import DashboardRepository

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardSnapshot, summary="Aggregated store overview")
def dashboard(user: CurrentUser, db: DatabaseDependency) -> DashboardSnapshot:
    return DashboardRepository(db).snapshot(user.store_id)
