"""Explainable customer intelligence."""

from fastapi import APIRouter

from app.api.dependencies import AgentUser, CurrentUser, DatabaseDependency
from app.domain.models import CustomerIntelligence, CustomerMergeInput
from app.services.customer_intelligence import (
    customer_intelligence,
    list_customer_intelligence,
    merge_customers,
)

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=list[CustomerIntelligence])
def customers(user: CurrentUser, db: DatabaseDependency) -> list[CustomerIntelligence]:
    return list_customer_intelligence(db, user.store_id)


@router.get("/{customer_id}", response_model=CustomerIntelligence)
def customer(
    customer_id: int, user: CurrentUser, db: DatabaseDependency
) -> CustomerIntelligence:
    return customer_intelligence(db, user.store_id, customer_id)


@router.post("/{customer_id}/merge", response_model=CustomerIntelligence)
def merge(
    customer_id: int,
    payload: CustomerMergeInput,
    user: AgentUser,
    db: DatabaseDependency,
) -> CustomerIntelligence:
    return merge_customers(
        db, user.store_id, customer_id, payload.source_customer_id
    )
