"""Store API key management for the website integration kit."""

from __future__ import annotations

from fastapi import APIRouter, status
from sqlalchemy import select

from app.api.dependencies import AdminUser, CurrentUser, DatabaseDependency
from app.db.models import ApiKeyModel
from app.domain.errors import InvalidInputError
from app.domain.models import ApiKeyCreatedResponse, ApiKeyCreateInput, ApiKeySummary
from app.repositories.audit_repository import AuditRepository
from app.services.api_keys import create_api_key, revoke_api_key

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


def _summary(row: ApiKeyModel) -> ApiKeySummary:
    return ApiKeySummary(
        id=row.id,
        name=row.name,
        key_prefix=row.key_prefix,
        key_type=row.key_type,
        scopes=list(row.scopes_json),
        allowed_origins=list(row.allowed_origins_json),
        is_active=row.is_active,
        created_at=row.created_at,
        last_used_at=row.last_used_at,
        revoked_at=row.revoked_at,
    )


@router.get("", response_model=list[ApiKeySummary])
def list_keys(user: CurrentUser, db: DatabaseDependency) -> list[ApiKeySummary]:
    rows = db.scalars(
        select(ApiKeyModel)
        .where(ApiKeyModel.store_id == user.store_id)
        .order_by(ApiKeyModel.created_at.desc())
    ).all()
    return [_summary(row) for row in rows]


@router.post(
    "",
    response_model=ApiKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a key; the plaintext is shown once and never stored",
)
def create_key(
    payload: ApiKeyCreateInput, user: AdminUser, db: DatabaseDependency
) -> ApiKeyCreatedResponse:
    try:
        row, plaintext = create_api_key(
            db,
            store_id=user.store_id,
            name=payload.name,
            allowed_origins=payload.allowed_origins,
        )
    except ValueError as exc:
        raise InvalidInputError(str(exc)) from exc
    AuditRepository(db).add(
        actor=user.email,
        action="api_key_created",
        entity_type="api_key",
        entity_id=str(row.id),
        metadata={"name": row.name, "prefix": row.key_prefix},
        organization_id=user.organization_id,
        store_id=user.store_id,
        actor_user_id=user.user_id,
    )
    return ApiKeyCreatedResponse(key=plaintext, api_key=_summary(row))


@router.post("/{key_id}/revoke", response_model=ApiKeySummary)
def revoke_key(key_id: int, user: AdminUser, db: DatabaseDependency) -> ApiKeySummary:
    row = revoke_api_key(db, store_id=user.store_id, key_id=key_id)
    AuditRepository(db).add(
        actor=user.email,
        action="api_key_revoked",
        entity_type="api_key",
        entity_id=str(row.id),
        metadata={"prefix": row.key_prefix},
        organization_id=user.organization_id,
        store_id=user.store_id,
        actor_user_id=user.user_id,
    )
    return _summary(row)
