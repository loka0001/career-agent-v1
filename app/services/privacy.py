"""Tenant data export, deletion workflows, and retention enforcement."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.db.models import (
    AIUsageRecordModel,
    ApiKeyModel,
    AuditEventModel,
    AuthSessionModel,
    AuthTokenModel,
    ConversationModel,
    CustomerConsentModel,
    CustomerIdentityModel,
    CustomerModel,
    DataDeletionRequestModel,
    EventModel,
    ExternalOperationModel,
    MediaAssetModel,
    MembershipModel,
    MessageModel,
    OAuthTransactionModel,
    OrderItemModel,
    OrderModel,
    ProductModel,
    ProviderConnectionModel,
    RetentionPolicyModel,
    SalesQueryModel,
    StoreModel,
    SubscriptionModel,
    UserModel,
)
from app.domain.errors import AuthenticationError, ConflictError, NotFoundError
from app.security import hash_opaque_token, verify_password
from app.services.job_queue import enqueue_job, job_handler

ACCOUNT_DELETION_GRACE_HOURS = 24
STORE_DELETION_GRACE_HOURS = 24


def _value(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _row(row: object, fields: tuple[str, ...]) -> dict[str, object]:
    return {field: _value(getattr(row, field)) for field in fields}


def export_customer_data(
    session: Session,
    store_id: str,
    customer_id: int,
) -> dict[str, object]:
    customer = session.scalar(
        select(CustomerModel).where(
            CustomerModel.id == customer_id,
            CustomerModel.store_id == store_id,
        )
    )
    if customer is None:
        raise NotFoundError(details={"entity": "customer"})
    conversations = session.scalars(
        select(ConversationModel).where(
            ConversationModel.store_id == store_id,
            ConversationModel.customer_id == customer_id,
        )
    ).all()
    conversation_ids = [item.id for item in conversations]
    messages = (
        session.scalars(
            select(MessageModel)
            .where(MessageModel.conversation_id.in_(conversation_ids))
            .order_by(MessageModel.created_at)
        ).all()
        if conversation_ids
        else []
    )
    orders = session.scalars(
        select(OrderModel)
        .where(
            OrderModel.store_id == store_id,
            OrderModel.customer_id == customer_id,
        )
        .order_by(OrderModel.created_at)
    ).all()
    order_ids = [item.id for item in orders]
    order_items = (
        session.scalars(select(OrderItemModel).where(OrderItemModel.order_id.in_(order_ids))).all()
        if order_ids
        else []
    )
    consents = session.scalars(
        select(CustomerConsentModel).where(
            CustomerConsentModel.store_id == store_id,
            CustomerConsentModel.customer_id == customer_id,
        )
    ).all()
    identities = session.scalars(
        select(CustomerIdentityModel).where(
            CustomerIdentityModel.store_id == store_id,
            CustomerIdentityModel.customer_id == customer_id,
        )
    ).all()
    return {
        "exported_at": datetime.now(UTC).isoformat(),
        "customer": _row(
            customer,
            (
                "id",
                "display_name",
                "phone",
                "email",
                "notes",
                "tags_json",
                "consent_json",
                "attributes_json",
                "first_seen_at",
                "last_seen_at",
            ),
        ),
        "identities": [
            _row(item, ("channel_type", "external_id", "created_at")) for item in identities
        ],
        "consents": [
            _row(
                item,
                ("channel_type", "status", "source", "consent_text", "occurred_at"),
            )
            for item in consents
        ],
        "conversations": [
            _row(item, ("id", "channel_id", "status", "created_at", "updated_at"))
            for item in conversations
        ],
        "messages": [
            _row(
                item,
                (
                    "id",
                    "conversation_id",
                    "direction",
                    "sender_type",
                    "body",
                    "attachments_json",
                    "status",
                    "created_at",
                ),
            )
            for item in messages
        ],
        "orders": [
            _row(
                item,
                (
                    "id",
                    "status",
                    "currency",
                    "subtotal_numeric",
                    "discount_numeric",
                    "total_numeric",
                    "shipping_json",
                    "notes",
                    "created_at",
                    "updated_at",
                ),
            )
            for item in orders
        ],
        "order_items": [
            _row(
                item,
                (
                    "order_id",
                    "product_id",
                    "product_name",
                    "unit_price_numeric",
                    "quantity",
                    "line_total_numeric",
                ),
            )
            for item in order_items
        ],
    }


def export_store_data(
    session: Session,
    store_id: str,
    user_id: str,
) -> dict[str, object]:
    store = session.get(StoreModel, store_id)
    user = session.get(UserModel, user_id)
    if store is None or user is None or store.organization_id is None:
        raise NotFoundError(details={"entity": "store"})
    products = session.scalars(select(ProductModel).where(ProductModel.store_id == store_id)).all()
    customers = session.scalars(
        select(CustomerModel).where(CustomerModel.store_id == store_id)
    ).all()
    providers = session.scalars(
        select(ProviderConnectionModel).where(ProviderConnectionModel.store_id == store_id)
    ).all()
    subscription = session.scalar(
        select(SubscriptionModel).where(SubscriptionModel.organization_id == store.organization_id)
    )
    return {
        "exported_at": datetime.now(UTC).isoformat(),
        "profile": _row(user, ("id", "email", "full_name", "created_at")),
        "store": _row(
            store,
            (
                "id",
                "organization_id",
                "slug",
                "name",
                "default_language",
                "created_at",
            ),
        ),
        "subscription": (
            _row(
                subscription,
                (
                    "plan_key",
                    "status",
                    "provider",
                    "trial_end",
                    "current_period_start",
                    "current_period_end",
                ),
            )
            if subscription
            else None
        ),
        "products": [
            _row(
                item,
                (
                    "product_id",
                    "name",
                    "category",
                    "price_numeric",
                    "stock",
                    "features_json",
                    "description",
                    "status",
                    "created_at",
                    "updated_at",
                ),
            )
            for item in products
        ],
        "customers": [export_customer_data(session, store_id, item.id) for item in customers],
        "provider_connections": [
            _row(
                item,
                (
                    "provider",
                    "connection_type",
                    "external_account_id",
                    "external_resource_id",
                    "display_name",
                    "scopes_json",
                    "capabilities_json",
                    "status",
                    "last_health_at",
                    "last_successful_sync_at",
                ),
            )
            for item in providers
        ],
        "ai_usage": [
            _row(
                item,
                (
                    "operation",
                    "provider",
                    "model",
                    "input_tokens",
                    "output_tokens",
                    "cost_numeric",
                    "created_at",
                ),
            )
            for item in session.scalars(
                select(AIUsageRecordModel).where(AIUsageRecordModel.store_id == store_id)
            ).all()
        ],
    }


def get_retention_policy(session: Session, store_id: str) -> RetentionPolicyModel:
    policy = session.get(RetentionPolicyModel, store_id)
    if policy is None:
        policy = RetentionPolicyModel(store_id=store_id)
        session.add(policy)
        session.flush()
    return policy


def update_retention_policy(
    session: Session,
    store_id: str,
    *,
    message_days: int,
    media_days: int,
    event_days: int,
) -> RetentionPolicyModel:
    policy = get_retention_policy(session, store_id)
    policy.message_days = message_days
    policy.media_days = media_days
    policy.event_days = event_days
    policy.updated_at = datetime.now(UTC)
    enqueue_job(
        session,
        job_type="privacy.retention",
        store_id=store_id,
        payload={"store_id": store_id},
        dedup_key=f"privacy-retention:{store_id}:{datetime.now(UTC).date().isoformat()}",
    )
    return policy


def _new_request(
    session: Session,
    *,
    scope: str,
    organization_id: str | None,
    store_id: str | None,
    user_id: str | None,
    customer_id: int | None = None,
    provider_user_id_hash: str | None = None,
    delay: timedelta,
) -> DataDeletionRequestModel:
    existing = session.scalar(
        select(DataDeletionRequestModel).where(
            DataDeletionRequestModel.scope == scope,
            DataDeletionRequestModel.store_id == store_id,
            DataDeletionRequestModel.user_id == user_id,
            DataDeletionRequestModel.customer_id == customer_id,
            DataDeletionRequestModel.status.in_(("pending", "running")),
        )
    )
    if existing is not None:
        return existing
    request = DataDeletionRequestModel(
        id=f"del_{uuid.uuid4().hex[:28]}",
        scope=scope,
        organization_id=organization_id,
        store_id=store_id,
        user_id=user_id,
        customer_id=customer_id,
        provider_user_id_hash=provider_user_id_hash,
        status="pending",
        execute_after=datetime.now(UTC) + delay,
    )
    session.add(request)
    session.flush()
    enqueue_job(
        session,
        job_type="privacy.delete",
        store_id=store_id,
        payload={"deletion_request_id": request.id},
        run_at=request.execute_after,
        dedup_key=f"privacy-delete:{request.id}",
        max_attempts=5,
    )
    return request


def request_account_deletion(
    session: Session,
    *,
    user_id: str,
    organization_id: str,
    store_id: str,
    password: str,
) -> DataDeletionRequestModel:
    user = session.get(UserModel, user_id)
    if user is None or not verify_password(password, user.password_hash):
        raise AuthenticationError("Password confirmation failed")
    request = _new_request(
        session,
        scope="account",
        organization_id=organization_id,
        store_id=store_id,
        user_id=user_id,
        delay=timedelta(hours=ACCOUNT_DELETION_GRACE_HOURS),
    )
    now = datetime.now(UTC)
    user.deletion_requested_at = now
    session.execute(
        update(AuthSessionModel)
        .where(
            AuthSessionModel.user_id == user_id,
            AuthSessionModel.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    session.add(
        AuditEventModel(
            organization_id=organization_id,
            store_id=store_id,
            actor_user_id=user_id,
            actor=user.email,
            action="privacy.account_deletion_requested",
            entity_type="user",
            entity_id=user_id,
            metadata_json={"request_id": request.id},
        )
    )
    return request


def _disconnect_store(session: Session, store_id: str) -> None:
    now = datetime.now(UTC)
    session.execute(
        update(ProviderConnectionModel)
        .where(ProviderConnectionModel.store_id == store_id)
        .values(
            credentials_json={},
            status="disconnected",
            token_expires_at=None,
            last_error_code=None,
            last_error_message=None,
            updated_at=now,
        )
    )
    session.execute(
        update(ApiKeyModel)
        .where(ApiKeyModel.store_id == store_id)
        .values(is_active=False, revoked_at=now)
    )
    session.execute(
        update(OAuthTransactionModel)
        .where(OAuthTransactionModel.store_id == store_id)
        .values(result_credentials_json={}, used_at=now)
    )


def request_store_deletion(
    session: Session,
    *,
    user_id: str,
    organization_id: str,
    store_id: str,
    password: str,
) -> DataDeletionRequestModel:
    user = session.get(UserModel, user_id)
    store = session.get(StoreModel, store_id)
    if user is None or store is None or not verify_password(password, user.password_hash):
        raise AuthenticationError("Password confirmation failed")
    request = _new_request(
        session,
        scope="store",
        organization_id=organization_id,
        store_id=store_id,
        user_id=user_id,
        delay=timedelta(hours=STORE_DELETION_GRACE_HOURS),
    )
    store.is_active = False
    store.deletion_requested_at = datetime.now(UTC)
    _disconnect_store(session, store_id)
    session.add(
        AuditEventModel(
            organization_id=organization_id,
            store_id=store_id,
            actor_user_id=user_id,
            actor=user.email,
            action="privacy.store_deletion_requested",
            entity_type="store",
            entity_id=store_id,
            metadata_json={"request_id": request.id},
        )
    )
    return request


def request_customer_deletion(
    session: Session,
    *,
    store_id: str,
    organization_id: str | None,
    customer_id: int,
    provider_user_id: str | None = None,
) -> DataDeletionRequestModel:
    customer = session.scalar(
        select(CustomerModel).where(
            CustomerModel.id == customer_id,
            CustomerModel.store_id == store_id,
        )
    )
    if customer is None:
        raise NotFoundError(details={"entity": "customer"})
    return _new_request(
        session,
        scope="customer",
        organization_id=organization_id,
        store_id=store_id,
        user_id=None,
        customer_id=customer_id,
        provider_user_id_hash=(hash_opaque_token(provider_user_id) if provider_user_id else None),
        delay=timedelta(),
    )


def _delete_customer_data(session: Session, store_id: str, customer_id: int) -> None:
    customer = session.scalar(
        select(CustomerModel).where(
            CustomerModel.id == customer_id,
            CustomerModel.store_id == store_id,
        )
    )
    if customer is None:
        return
    conversation_ids = session.scalars(
        select(ConversationModel.id).where(
            ConversationModel.store_id == store_id,
            ConversationModel.customer_id == customer_id,
        )
    ).all()
    if conversation_ids:
        session.execute(
            update(MessageModel)
            .where(MessageModel.conversation_id.in_(conversation_ids))
            .values(
                body="[deleted by privacy request]",
                attachments_json=[],
                metadata_json={},
                error_message=None,
            )
        )
        session.execute(
            update(ConversationModel)
            .where(ConversationModel.id.in_(conversation_ids))
            .values(last_message_preview="[deleted]", tags_json=[])
        )
    session.execute(
        delete(CustomerIdentityModel).where(
            CustomerIdentityModel.store_id == store_id,
            CustomerIdentityModel.customer_id == customer_id,
        )
    )
    session.execute(
        delete(EventModel).where(
            EventModel.store_id == store_id,
            EventModel.customer_id == customer_id,
        )
    )
    customer.display_name = "Deleted customer"
    customer.phone = None
    customer.email = None
    customer.notes = ""
    customer.tags_json = []
    customer.consent_json = {}
    customer.attributes_json = {}


def _delete_store_data(session: Session, store_id: str) -> None:
    store = session.get(StoreModel, store_id)
    if store is None:
        return
    _disconnect_store(session, store_id)
    customer_ids = session.scalars(
        select(CustomerModel.id).where(CustomerModel.store_id == store_id)
    ).all()
    for customer_id in customer_ids:
        _delete_customer_data(session, store_id, customer_id)
    session.execute(delete(EventModel).where(EventModel.store_id == store_id))
    session.execute(delete(MediaAssetModel).where(MediaAssetModel.store_id == store_id))
    session.execute(delete(SalesQueryModel).where(SalesQueryModel.store_id == store_id))
    session.execute(
        delete(ExternalOperationModel).where(ExternalOperationModel.store_id == store_id)
    )
    session.execute(
        update(OrderModel).where(OrderModel.store_id == store_id).values(shipping_json={}, notes="")
    )
    session.execute(
        update(ProductModel)
        .where(ProductModel.store_id == store_id)
        .values(
            description="[retained order reference]",
            features_json=[],
            benefits_json=[],
            image_summary="",
            original_image_url="",
            public_image_url=None,
            stock=0,
        )
    )
    store.name = "Deleted store"
    store.is_active = False
    store.deleted_at = datetime.now(UTC)


def _delete_account_data(session: Session, user_id: str) -> None:
    user = session.get(UserModel, user_id)
    if user is None:
        return
    email = user.email
    memberships = session.scalars(
        select(MembershipModel).where(MembershipModel.user_id == user_id)
    ).all()
    for membership in memberships:
        other_owner_count = int(
            session.scalar(
                select(func.count(MembershipModel.id)).where(
                    MembershipModel.organization_id == membership.organization_id,
                    MembershipModel.user_id != user_id,
                    MembershipModel.role == "owner",
                )
            )
            or 0
        )
        if membership.role == "owner" and other_owner_count == 0:
            store_ids = session.scalars(
                select(StoreModel.id).where(
                    StoreModel.organization_id == membership.organization_id
                )
            ).all()
            for store_id in store_ids:
                _delete_store_data(session, store_id)
    session.execute(delete(MembershipModel).where(MembershipModel.user_id == user_id))
    session.execute(delete(AuthSessionModel).where(AuthSessionModel.user_id == user_id))
    session.execute(delete(AuthTokenModel).where(AuthTokenModel.user_id == user_id))
    actor_hash = hash_opaque_token(email)[:16]
    session.execute(
        update(AuditEventModel)
        .where(AuditEventModel.actor_user_id == user_id)
        .values(
            actor=f"deleted-user:{actor_hash}",
            actor_user_id=None,
        )
    )
    user.email = f"deleted+{actor_hash}@invalid.local"
    user.full_name = ""
    user.password_hash = "deleted"
    user.mfa_secret_json = {}
    user.mfa_enabled = False
    user.is_active = False
    user.deleted_at = datetime.now(UTC)


@job_handler("privacy.delete")
def execute_deletion_job(session: Session, payload: dict[str, Any]) -> None:
    request = session.get(
        DataDeletionRequestModel,
        str(payload["deletion_request_id"]),
    )
    if request is None or request.status == "completed":
        return
    now = datetime.now(UTC)
    execute_after = request.execute_after
    if execute_after.tzinfo is None:
        execute_after = execute_after.replace(tzinfo=UTC)
    if execute_after > now:
        raise ConflictError("Deletion grace period has not elapsed")
    request.status = "running"
    if request.scope == "account" and request.user_id:
        _delete_account_data(session, request.user_id)
    elif request.scope == "store" and request.store_id:
        _delete_store_data(session, request.store_id)
    elif request.scope == "customer" and request.store_id and request.customer_id:
        _delete_customer_data(session, request.store_id, request.customer_id)
    else:
        raise ConflictError("Deletion request scope is incomplete")
    request.status = "completed"
    request.completed_at = now
    request.last_error = None


@job_handler("privacy.retention")
def enforce_retention_job(session: Session, payload: dict[str, Any]) -> None:
    store_id = str(payload["store_id"])
    policy = get_retention_policy(session, store_id)
    now = datetime.now(UTC)
    conversation_ids = select(ConversationModel.id).where(ConversationModel.store_id == store_id)
    session.execute(
        delete(MessageModel).where(
            MessageModel.conversation_id.in_(conversation_ids),
            MessageModel.created_at < now - timedelta(days=policy.message_days),
        )
    )
    session.execute(
        delete(EventModel).where(
            EventModel.store_id == store_id,
            EventModel.created_at < now - timedelta(days=policy.event_days),
        )
    )
    session.execute(
        delete(SalesQueryModel).where(
            SalesQueryModel.store_id == store_id,
            SalesQueryModel.created_at < now - timedelta(days=policy.message_days),
        )
    )
    session.execute(
        delete(MediaAssetModel).where(
            MediaAssetModel.store_id == store_id,
            MediaAssetModel.is_public.is_(False),
            MediaAssetModel.created_at < now - timedelta(days=policy.media_days),
        )
    )


def verify_meta_signed_request(signed_request: str, app_secret: str) -> str:
    try:
        encoded_signature, encoded_payload = signed_request.split(".", 1)
        signature = base64.urlsafe_b64decode(
            encoded_signature + "=" * (-len(encoded_signature) % 4)
        )
        expected = hmac.new(
            app_secret.encode(),
            encoded_payload.encode(),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(signature, expected):
            raise AuthenticationError("Invalid Meta deletion signature")
        payload = json.loads(
            base64.urlsafe_b64decode(encoded_payload + "=" * (-len(encoded_payload) % 4))
        )
        user_id = str(payload["user_id"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise AuthenticationError("Invalid Meta deletion request") from exc
    if not user_id:
        raise AuthenticationError("Invalid Meta deletion request")
    return user_id


def request_meta_user_deletion(
    session: Session,
    provider_user_id: str,
) -> DataDeletionRequestModel:
    identity = session.scalar(
        select(CustomerIdentityModel).where(
            CustomerIdentityModel.external_id == provider_user_id,
            CustomerIdentityModel.channel_type.in_(
                ("messenger", "instagram_dm", "facebook_comments", "instagram_comments")
            ),
        )
    )
    if identity is None:
        request = _new_request(
            session,
            scope="customer",
            organization_id=None,
            store_id=None,
            user_id=None,
            provider_user_id_hash=hash_opaque_token(provider_user_id),
            delay=timedelta(),
        )
        request.status = "completed"
        request.completed_at = datetime.now(UTC)
        return request
    store = session.get(StoreModel, identity.store_id)
    return request_customer_deletion(
        session,
        store_id=identity.store_id,
        organization_id=store.organization_id if store else None,
        customer_id=identity.customer_id,
        provider_user_id=provider_user_id,
    )
