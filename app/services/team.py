"""Organization team management with role-escalation safeguards."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import AuthTokenModel, MembershipModel, UserModel
from app.domain.enums import MemberRole
from app.domain.errors import AuthenticationError, AuthorizationError, ConflictError, NotFoundError
from app.domain.models import AuthUser, TeamInviteInput, TeamInviteResult, TeamMemberOut
from app.integrations.email import EmailSender
from app.repositories.tenant_repository import TenantRepository
from app.security import hash_password, verify_password
from app.services.auth_lifecycle import (
    TEAM_INVITE,
    consume_auth_token,
    create_auth_token,
    deliver_action_email,
    ensure_password_strength,
)
from app.services.billing import check_resource_limit


def _out(membership: MembershipModel, user: UserModel) -> TeamMemberOut:
    return TeamMemberOut(
        membership_id=membership.id,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=MemberRole(membership.role),
        created_at=membership.created_at,
    )


def list_team(session: Session, organization_id: str) -> list[TeamMemberOut]:
    rows = session.execute(
        select(MembershipModel, UserModel)
        .join(UserModel, UserModel.id == MembershipModel.user_id)
        .where(MembershipModel.organization_id == organization_id)
        .order_by(MembershipModel.created_at)
    ).all()
    return [_out(membership, user) for membership, user in rows]


def _membership(session: Session, organization_id: str, membership_id: int) -> MembershipModel:
    row = session.scalar(
        select(MembershipModel).where(
            MembershipModel.id == membership_id,
            MembershipModel.organization_id == organization_id,
        )
    )
    if row is None:
        raise NotFoundError(details={"entity": "membership"})
    return row


def _protect_owner(actor: AuthUser, current_role: MemberRole, next_role: MemberRole) -> None:
    if next_role == MemberRole.OWNER and actor.role != MemberRole.OWNER:
        raise AuthorizationError("Only an owner can assign the owner role")
    if current_role == MemberRole.OWNER and actor.role != MemberRole.OWNER:
        raise AuthorizationError("Only an owner can change another owner")


def invite_member(
    session: Session,
    actor: AuthUser,
    payload: TeamInviteInput,
    sender: EmailSender,
    settings: Settings,
) -> TeamInviteResult:
    if payload.role == MemberRole.OWNER and actor.role != MemberRole.OWNER:
        raise AuthorizationError("Only an owner can assign the owner role")
    existing_user = session.scalar(
        select(UserModel).where(UserModel.email == payload.email.casefold())
    )
    if existing_user is not None:
        existing_membership = session.scalar(
            select(MembershipModel).where(
                MembershipModel.organization_id == actor.organization_id,
                MembershipModel.user_id == existing_user.id,
            )
        )
        if existing_membership is not None:
            raise ConflictError("User is already a member", details={"field": "email"})

    member_count = session.scalar(
        select(func.count(MembershipModel.id)).where(
            MembershipModel.organization_id == actor.organization_id
        )
    )
    pending_count = session.scalar(
        select(func.count(AuthTokenModel.id)).where(
            AuthTokenModel.organization_id == actor.organization_id,
            AuthTokenModel.purpose == TEAM_INVITE,
            AuthTokenModel.used_at.is_(None),
            AuthTokenModel.expires_at > datetime.now(UTC),
        )
    )
    check_resource_limit(
        session,
        actor.store_id,
        "team_members",
        int(member_count or 0) + int(pending_count or 0),
    )
    token_row, plaintext = create_auth_token(
        session,
        purpose=TEAM_INVITE,
        email=payload.email,
        user_id=existing_user.id if existing_user is not None else None,
        organization_id=actor.organization_id,
        metadata={"role": payload.role.value, "full_name": payload.full_name},
        ttl=timedelta(days=7),
    )
    deliver_action_email(
        sender,
        to=payload.email.casefold(),
        subject="دعوة للانضمام إلى Commerce AI",
        text="تمت دعوتك للانضمام إلى فريق المتجر. اختر كلمة مرورك لإتمام الانضمام.",
        public_base_url=settings.public_base_url,
        route="/accept-invite",
        token=plaintext,
        idempotency_key=f"invite-{token_row.id}",
    )
    return TeamInviteResult(
        invite_id=token_row.id,
        email=token_row.email,
        role=payload.role,
        status="pending",
        expires_at=token_row.expires_at,
    )


def accept_invite(
    session: Session,
    *,
    token: str,
    password: str,
    full_name: str,
) -> AuthUser:
    ensure_password_strength(password)
    invitation = consume_auth_token(session, token, TEAM_INVITE)
    if invitation.organization_id is None:
        raise AuthenticationError("Invitation has no organization")
    role_value = str(invitation.metadata_json.get("role", MemberRole.AGENT.value))
    try:
        role = MemberRole(role_value)
    except ValueError as exc:
        raise AuthenticationError("Invitation role is invalid") from exc
    tenants = TenantRepository(session)
    user = tenants.get_user_by_email(invitation.email)
    if user is None:
        user = UserModel(
            id=f"usr_{uuid.uuid4().hex[:12]}",
            email=invitation.email,
            full_name=full_name or str(invitation.metadata_json.get("full_name", "")),
            password_hash=hash_password(password),
            email_verified_at=datetime.now(UTC),
        )
        session.add(user)
        session.flush()
    else:
        if not user.is_active or not verify_password(password, user.password_hash):
            raise AuthenticationError("Existing users must enter their current password")
        user.email_verified_at = user.email_verified_at or datetime.now(UTC)
        if full_name and not user.full_name:
            user.full_name = full_name
    tenants.add_member(
        organization_id=invitation.organization_id,
        user_id=user.id,
        role=role,
    )
    store = tenants.default_store_for_user(user.id)
    return tenants.resolve_access(user_id=user.id, store_id=store.store_id)


def update_member_role(
    session: Session, actor: AuthUser, membership_id: int, role: MemberRole
) -> TeamMemberOut:
    membership = _membership(session, actor.organization_id, membership_id)
    current_role = MemberRole(membership.role)
    _protect_owner(actor, current_role, role)
    if current_role == MemberRole.OWNER and role != MemberRole.OWNER:
        owners = session.scalar(
            select(func.count(MembershipModel.id)).where(
                MembershipModel.organization_id == actor.organization_id,
                MembershipModel.role == MemberRole.OWNER.value,
            )
        )
        if int(owners or 0) <= 1:
            raise ConflictError("The organization must keep at least one owner")
    membership.role = role.value
    user = session.get(UserModel, membership.user_id)
    if user is None:
        raise NotFoundError(details={"entity": "user"})
    session.flush()
    return _out(membership, user)


def revoke_member(session: Session, actor: AuthUser, membership_id: int) -> None:
    membership = _membership(session, actor.organization_id, membership_id)
    role = MemberRole(membership.role)
    _protect_owner(actor, role, MemberRole.AGENT)
    if membership.user_id == actor.user_id:
        raise ConflictError("You cannot revoke your own membership")
    session.delete(membership)
    session.flush()
