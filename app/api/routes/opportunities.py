"""Revenue Opportunity Engine endpoints."""

from fastapi import APIRouter, status

from app.api.dependencies import AgentUser, CurrentUser, DatabaseDependency
from app.api.schemas import MessageResponse
from app.domain.models import (
    OpportunityDashboard,
    OpportunityDecisionInput,
    OpportunityOut,
)
from app.services.opportunities import (
    decide_opportunity,
    enqueue_opportunity_scan,
    list_opportunities,
    opportunity_dashboard,
)
from app.services.billing import require_feature

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.get("", response_model=list[OpportunityOut])
def opportunities(user: CurrentUser, db: DatabaseDependency) -> list[OpportunityOut]:
    require_feature(db, user.store_id, "opportunities")
    return list_opportunities(db, user.store_id)


@router.get("/dashboard", response_model=OpportunityDashboard)
def dashboard(
    user: CurrentUser, db: DatabaseDependency
) -> OpportunityDashboard:
    require_feature(db, user.store_id, "opportunities")
    return opportunity_dashboard(db, user.store_id)


@router.post("/scan", response_model=MessageResponse, status_code=status.HTTP_202_ACCEPTED)
def scan(user: AgentUser, db: DatabaseDependency) -> MessageResponse:
    require_feature(db, user.store_id, "opportunities")
    enqueue_opportunity_scan(db, user.store_id)
    return MessageResponse(message="opportunity_scan_queued")


@router.post("/{opportunity_id}/decision", response_model=OpportunityOut)
def decide(
    opportunity_id: int,
    payload: OpportunityDecisionInput,
    user: AgentUser,
    db: DatabaseDependency,
) -> OpportunityOut:
    require_feature(db, user.store_id, "opportunities")
    return decide_opportunity(
        db,
        user.store_id,
        opportunity_id,
        payload.decision,
        user.user_id,
        payload.realized_revenue,
    )
