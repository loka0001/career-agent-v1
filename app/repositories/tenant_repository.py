"""Organizations, users, memberships, and tenant access resolution."""

from __future__ import annotations

import re
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import MembershipModel, OrganizationModel, StoreModel, UserModel
from app.domain.enums import MemberRole
from app.domain.errors import AuthorizationError, ConflictError, NotFoundError
from app.domain.models import AuthUser, StoreSummary


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return normalized or "store"


class TenantRepository:
    def __init__(self, session: Session):
        self._session = session

    def get_user_by_email(self, email: str) -> UserModel | None:
        return self._session.scalar(select(UserModel).where(UserModel.email == email.casefold()))

    def create_tenant(
        self,
        *,
        organization_name: str,
        store_name: str,
        email: str,
        password_hash: str,
        full_name: str = "",
        plan: str = "starter",
        default_language: str = "ar",
    ) -> tuple[UserModel, OrganizationModel, StoreModel]:
        normalized_email = email.casefold()
        if self.get_user_by_email(normalized_email) is not None:
            raise ConflictError("Email already registered", details={"field": "email"})
        suffix = uuid.uuid4().hex[:8]
        organization = OrganizationModel(
            id=f"org_{uuid.uuid4().hex[:12]}", name=organization_name, plan=plan
        )
        user = UserModel(
            id=f"usr_{uuid.uuid4().hex[:12]}",
            email=normalized_email,
            password_hash=password_hash,
            full_name=full_name,
        )
        store = StoreModel(
            id=f"st_{uuid.uuid4().hex[:12]}",
            organization_id=organization.id,
            slug=f"{_slugify(store_name)}-{suffix}",
            name=store_name,
            default_language=default_language,
        )
        self._session.add_all([organization, user, store])
        self._session.flush()
        self._session.add(
            MembershipModel(
                organization_id=organization.id, user_id=user.id, role=MemberRole.OWNER.value
            )
        )
        self._session.flush()
        return user, organization, store

    def add_member(
        self, *, organization_id: str, user_id: str, role: MemberRole
    ) -> MembershipModel:
        existing = self._session.scalar(
            select(MembershipModel).where(
                MembershipModel.organization_id == organization_id,
                MembershipModel.user_id == user_id,
            )
        )
        if existing is not None:
            existing.role = role.value
            self._session.flush()
            return existing
        membership = MembershipModel(
            organization_id=organization_id, user_id=user_id, role=role.value
        )
        self._session.add(membership)
        self._session.flush()
        return membership

    def resolve_access(self, *, user_id: str, store_id: str) -> AuthUser:
        """Authoritative check that the user may act on the store; returns full context."""

        row = self._session.execute(
            select(UserModel, StoreModel, MembershipModel.role)
            .select_from(UserModel)
            .join(MembershipModel, MembershipModel.user_id == UserModel.id)
            .join(
                StoreModel,
                StoreModel.organization_id == MembershipModel.organization_id,
            )
            .where(
                UserModel.id == user_id,
                StoreModel.id == store_id,
                UserModel.is_active.is_(True),
                StoreModel.is_active.is_(True),
            )
        ).first()
        if row is None:
            raise AuthorizationError("No access to this store")
        user, store, role = row
        if store.organization_id is None:
            raise AuthorizationError("Store is not attached to an organization")
        return AuthUser(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            store_id=store.id,
            organization_id=store.organization_id,
            role=MemberRole(role),
            email_verified=user.email_verified_at is not None,
            mfa_enabled=user.mfa_enabled,
        )

    def stores_for_user(self, user_id: str) -> list[StoreSummary]:
        rows = self._session.execute(
            select(StoreModel, MembershipModel.role)
            .select_from(MembershipModel)
            .join(
                StoreModel,
                StoreModel.organization_id == MembershipModel.organization_id,
            )
            .where(
                MembershipModel.user_id == user_id,
                StoreModel.is_active.is_(True),
            )
            .order_by(StoreModel.created_at)
        ).all()
        return [
            StoreSummary(
                store_id=store.id,
                name=store.name,
                organization_id=store.organization_id or "",
                role=MemberRole(role),
            )
            for store, role in rows
        ]

    def default_store_for_user(self, user_id: str) -> StoreSummary:
        stores = self.stores_for_user(user_id)
        if not stores:
            raise NotFoundError(details={"entity": "store", "user_id": user_id})
        return stores[0]
