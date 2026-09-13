"""Organization members and role management."""

from fastapi import APIRouter

from app.api.dependencies import AdminUser, ContainerDependency, CurrentUser, DatabaseDependency
from app.api.schemas import MessageResponse
from app.domain.models import (
    TeamInviteInput,
    TeamInviteResult,
    TeamMemberOut,
    TeamRoleUpdate,
)
from app.services.team import (
    invite_member,
    list_team,
    revoke_member,
    update_member_role,
)

router = APIRouter(prefix="/team", tags=["team"])


@router.get("", response_model=list[TeamMemberOut])
def team(user: CurrentUser, db: DatabaseDependency) -> list[TeamMemberOut]:
    return list_team(db, user.organization_id)


@router.post("", response_model=TeamInviteResult, status_code=201)
def invite(
    payload: TeamInviteInput,
    user: AdminUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> TeamInviteResult:
    return invite_member(
        db,
        user,
        payload,
        container.email_sender,
        container.settings,
    )


@router.patch("/{membership_id}", response_model=TeamMemberOut)
def change_role(
    membership_id: int,
    payload: TeamRoleUpdate,
    user: AdminUser,
    db: DatabaseDependency,
) -> TeamMemberOut:
    return update_member_role(db, user, membership_id, payload.role)


@router.post("/{membership_id}/revoke", response_model=MessageResponse)
def revoke(
    membership_id: int,
    user: AdminUser,
    db: DatabaseDependency,
) -> MessageResponse:
    revoke_member(db, user, membership_id)
    return MessageResponse(message="membership_revoked")
