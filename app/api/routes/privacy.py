"""Privacy export, retention, deletion, and legal policy endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Form, status
from sqlalchemy import select

from app.api.dependencies import (
    AdminReadUser,
    AdminUser,
    ContainerDependency,
    CsrfUser,
    CurrentUser,
    DatabaseDependency,
    OwnerUser,
)
from app.db.models import DataDeletionRequestModel, MediaAssetModel
from app.domain.errors import (
    AuthorizationError,
    IntegrationNotConfiguredError,
    NotFoundError,
)
from app.domain.models import (
    DeletionConfirmationInput,
    DeletionRequestOut,
    RetentionPolicyInput,
    RetentionPolicyOut,
)
from app.security import create_signed_resource_token
from app.services.privacy import (
    export_customer_data,
    export_store_data,
    get_retention_policy,
    request_account_deletion,
    request_meta_user_deletion,
    request_store_deletion,
    update_retention_policy,
    verify_meta_signed_request,
)

router = APIRouter(prefix="/privacy", tags=["privacy"])
webhook_router = APIRouter(prefix="/webhooks/meta", tags=["meta-data-deletion"])
legal_router = APIRouter(prefix="/legal", tags=["legal"])


def _deletion_out(row: DataDeletionRequestModel) -> DeletionRequestOut:
    return DeletionRequestOut(
        request_id=row.id,
        scope=row.scope,
        status=row.status,
        execute_after=row.execute_after,
        requested_at=row.requested_at,
        completed_at=row.completed_at,
    )


@router.get("/export")
def export_my_store(user: CurrentUser, db: DatabaseDependency) -> dict[str, object]:
    return export_store_data(db, user.store_id, user.user_id)


@router.get("/customers/{customer_id}/export")
def export_customer(
    customer_id: int,
    user: AdminReadUser,
    db: DatabaseDependency,
) -> dict[str, object]:
    return export_customer_data(db, user.store_id, customer_id)


@router.get("/retention", response_model=RetentionPolicyOut)
def retention_policy(
    user: AdminReadUser,
    db: DatabaseDependency,
) -> RetentionPolicyOut:
    row = get_retention_policy(db, user.store_id)
    return RetentionPolicyOut.model_validate(row, from_attributes=True)


@router.put("/retention", response_model=RetentionPolicyOut)
def set_retention_policy(
    payload: RetentionPolicyInput,
    user: AdminUser,
    db: DatabaseDependency,
) -> RetentionPolicyOut:
    row = update_retention_policy(
        db,
        user.store_id,
        message_days=payload.message_days,
        media_days=payload.media_days,
        event_days=payload.event_days,
    )
    return RetentionPolicyOut.model_validate(row, from_attributes=True)


@router.post(
    "/account-deletion",
    response_model=DeletionRequestOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def delete_account(
    payload: DeletionConfirmationInput,
    user: CsrfUser,
    db: DatabaseDependency,
) -> DeletionRequestOut:
    row = request_account_deletion(
        db,
        user_id=user.user_id,
        organization_id=user.organization_id,
        store_id=user.store_id,
        password=payload.password,
    )
    return _deletion_out(row)


@router.post(
    "/store-deletion",
    response_model=DeletionRequestOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def delete_store(
    payload: DeletionConfirmationInput,
    user: OwnerUser,
    db: DatabaseDependency,
) -> DeletionRequestOut:
    row = request_store_deletion(
        db,
        user_id=user.user_id,
        organization_id=user.organization_id,
        store_id=user.store_id,
        password=payload.password,
    )
    return _deletion_out(row)


@router.get("/deletions/{request_id}", response_model=DeletionRequestOut)
def deletion_status(
    request_id: str,
    user: CurrentUser,
    db: DatabaseDependency,
) -> DeletionRequestOut:
    row = db.get(DataDeletionRequestModel, request_id)
    if row is None:
        raise NotFoundError(details={"entity": "deletion_request"})
    if (
        row.organization_id != user.organization_id
        and row.user_id != user.user_id
        and row.store_id != user.store_id
    ):
        raise AuthorizationError()
    return _deletion_out(row)


@router.get("/media/{asset_id}/url")
def refresh_private_media_url(
    asset_id: str,
    user: CurrentUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> dict[str, str]:
    asset = db.scalar(
        select(MediaAssetModel).where(
            MediaAssetModel.id == asset_id,
            MediaAssetModel.store_id == user.store_id,
            MediaAssetModel.is_public.is_(False),
        )
    )
    if asset is None:
        raise NotFoundError(details={"entity": "media"})
    token = create_signed_resource_token(
        f"database-media:{asset_id}",
        ttl_seconds=24 * 60 * 60,
        secret_key=container.settings.effective_secret_key,
    )
    return {
        "url": (
            f"{container.settings.public_base_url.rstrip('/')}/media/{asset_id}"
            f"?token={token}"
        )
    }


@webhook_router.post("/data-deletion")
def meta_data_deletion(
    container: ContainerDependency,
    db: DatabaseDependency,
    signed_request: Annotated[str, Form()],
) -> dict[str, str]:
    app_secret = container.settings.meta_app_secret.get_secret_value()
    if not app_secret:
        raise IntegrationNotConfiguredError("Meta App is not configured")
    provider_user_id = verify_meta_signed_request(signed_request, app_secret)
    row = request_meta_user_deletion(db, provider_user_id)
    return {
        "url": (
            f"{container.settings.public_base_url.rstrip('/')}"
            f"/api/v1/privacy/public-deletions/{row.id}"
        ),
        "confirmation_code": row.id,
    }


@router.get("/public-deletions/{request_id}")
def public_deletion_status(
    request_id: str,
    db: DatabaseDependency,
) -> dict[str, str | None]:
    row = db.get(DataDeletionRequestModel, request_id)
    if row is None or row.provider_user_id_hash is None:
        raise NotFoundError(details={"entity": "deletion_request"})
    return {
        "confirmation_code": row.id,
        "status": row.status,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


@legal_router.get("/privacy")
def privacy_policy() -> dict[str, object]:
    return {
        "title": "Privacy Policy",
        "controller": "[COMPANY LEGAL NAME]",
        "jurisdiction": "[COUNTRY / JURISDICTION]",
        "effective_date": "[EFFECTIVE DATE]",
        "summary": [
            "We process merchant, customer, conversation, order, and integration data only to provide the service.",
            "Merchants control customer data and must have a lawful basis for messaging and tracking.",
            "Data export and deletion requests are available from authenticated settings.",
            "Financial transaction records may be retained where law requires after personal fields are removed.",
            "Contact [PRIVACY CONTACT EMAIL] for legal privacy requests.",
        ],
        "certifications": [],
    }


@legal_router.get("/terms")
def terms_of_service() -> dict[str, object]:
    return {
        "title": "Terms of Service",
        "provider": "[COMPANY LEGAL NAME]",
        "jurisdiction": "[COUNTRY / JURISDICTION]",
        "effective_date": "[EFFECTIVE DATE]",
        "summary": [
            "The merchant is responsible for catalog accuracy, customer consent, and provider account permissions.",
            "Automated content and replies require merchant review where configured.",
            "External providers may suspend or change their APIs independently.",
            "Service limits follow the active plan or trial shown in the product.",
            "Contact [LEGAL CONTACT EMAIL] for contractual notices.",
        ],
    }
