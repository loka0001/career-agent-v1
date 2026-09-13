"""Tenant-scoped analytics with period and channel filters."""

from datetime import datetime

from fastapi import APIRouter

from app.api.dependencies import CurrentUser, DatabaseDependency
from app.domain.models import AnalyticsSnapshot
from app.services.analytics import analytics_snapshot
from app.services.billing import require_feature

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("", response_model=AnalyticsSnapshot)
def analytics(
    user: CurrentUser,
    db: DatabaseDependency,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    channel: str | None = None,
) -> AnalyticsSnapshot:
    require_feature(db, user.store_id, "analytics")
    return analytics_snapshot(
        db,
        user.store_id,
        period_start=period_start,
        period_end=period_end,
        channel=channel,
    )
