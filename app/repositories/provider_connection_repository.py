"""Tenant-scoped persistence for provider connections and OAuth transactions."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from app.db.models import OAuthTransactionModel, ProviderConnectionModel
from app.domain.enums import ProviderCapability, ProviderConnectionStatus
from app.domain.errors import AuthenticationError, ConflictError, NotFoundError
from app.services.credential_vault import (
    decrypt_configured_credentials,
    encrypt_configured_credentials,
)

CAPABILITY_REGISTRY: dict[tuple[str, str], tuple[ProviderCapability, ...]] = {
    ("meta", "facebook_page"): (
        ProviderCapability.MESSAGING,
        ProviderCapability.COMMENTS,
        ProviderCapability.PUBLISHING,
    ),
    ("meta", "instagram_business"): (
        ProviderCapability.MESSAGING,
        ProviderCapability.COMMENTS,
        ProviderCapability.PUBLISHING,
    ),
    ("meta", "whatsapp_business"): (
        ProviderCapability.MESSAGING,
        ProviderCapability.TEMPLATES,
    ),
    ("shopify", "store"): (
        ProviderCapability.CATALOG_SYNC,
        ProviderCapability.ORDER_SYNC,
    ),
    ("woocommerce", "store"): (
        ProviderCapability.CATALOG_SYNC,
        ProviderCapability.ORDER_SYNC,
    ),
    ("generic_website", "site"): (
        ProviderCapability.CATALOG_SYNC,
        ProviderCapability.ORDER_SYNC,
    ),
}


def capabilities_for(provider: str, connection_type: str) -> list[str]:
    return [item.value for item in CAPABILITY_REGISTRY.get((provider, connection_type), ())]


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


class ProviderConnectionRepository:
    def __init__(self, session: Session, store_id: str):
        self._session = session
        self._store_id = store_id

    def list_all(self) -> list[ProviderConnectionModel]:
        return list(
            self._session.scalars(
                select(ProviderConnectionModel)
                .where(ProviderConnectionModel.store_id == self._store_id)
                .order_by(
                    ProviderConnectionModel.provider,
                    ProviderConnectionModel.connection_type,
                    ProviderConnectionModel.created_at,
                )
            ).all()
        )

    def get(self, connection_id: str) -> ProviderConnectionModel:
        row = self._session.scalar(
            select(ProviderConnectionModel).where(
                ProviderConnectionModel.id == connection_id,
                ProviderConnectionModel.store_id == self._store_id,
            )
        )
        if row is None:
            raise NotFoundError(details={"entity": "provider_connection"})
        return row

    def credentials(self, connection_id: str) -> dict[str, str]:
        return decrypt_configured_credentials(dict(self.get(connection_id).credentials_json))

    def upsert(
        self,
        *,
        provider: str,
        connection_type: str,
        external_resource_id: str,
        credentials: dict[str, str],
        display_name: str = "",
        external_account_id: str | None = None,
        external_business_id: str | None = None,
        scopes: list[str] | None = None,
        token_expires_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
        status: ProviderConnectionStatus = ProviderConnectionStatus.PENDING,
    ) -> ProviderConnectionModel:
        row = self._session.scalar(
            select(ProviderConnectionModel).where(
                ProviderConnectionModel.store_id == self._store_id,
                ProviderConnectionModel.provider == provider,
                ProviderConnectionModel.connection_type == connection_type,
                ProviderConnectionModel.external_resource_id == external_resource_id,
            )
        )
        now = datetime.now(UTC)
        if row is None:
            row = ProviderConnectionModel(
                id=f"conn_{uuid.uuid4().hex}",
                store_id=self._store_id,
                provider=provider,
                connection_type=connection_type,
                external_resource_id=external_resource_id,
                created_at=now,
            )
            self._session.add(row)
        row.external_account_id = external_account_id
        row.external_business_id = external_business_id
        row.display_name = display_name
        row.credentials_json = encrypt_configured_credentials(credentials)
        row.scopes_json = sorted(set(scopes or []))
        row.capabilities_json = capabilities_for(provider, connection_type)
        row.status = status.value
        row.token_expires_at = token_expires_at
        row.last_health_at = now if status == ProviderConnectionStatus.CONNECTED else None
        row.last_error_code = None
        row.last_error_message = None
        row.metadata_json = metadata or {}
        row.updated_at = now
        self._session.flush()
        return row

    def disconnect(self, connection_id: str) -> ProviderConnectionModel:
        row = self.get(connection_id)
        row.credentials_json = {}
        row.status = ProviderConnectionStatus.DISCONNECTED.value
        row.token_expires_at = None
        row.last_error_code = None
        row.last_error_message = None
        row.updated_at = datetime.now(UTC)
        self._session.flush()
        return row


class OAuthTransactionRepository:
    def __init__(self, session: Session):
        self._session = session

    def create(
        self,
        *,
        provider: str,
        store_id: str,
        user_id: str,
        ttl_seconds: int = 600,
    ) -> tuple[OAuthTransactionModel, str]:
        opaque_state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(24)
        state = f"{opaque_state}.{nonce}"
        now = datetime.now(UTC)
        row = OAuthTransactionModel(
            id=f"oauth_{uuid.uuid4().hex}",
            provider=provider,
            store_id=store_id,
            user_id=user_id,
            state_hash=_hash(opaque_state),
            nonce_hash=_hash(nonce),
            expires_at=now + timedelta(seconds=ttl_seconds),
            created_at=now,
        )
        self._session.add(row)
        self._session.flush()
        return row, state

    def _resolve(
        self,
        *,
        state: str,
        provider: str,
        store_id: str,
        user_id: str,
    ) -> OAuthTransactionModel:
        try:
            opaque_state, nonce = state.split(".", 1)
        except ValueError as exc:
            raise AuthenticationError("Invalid OAuth state") from exc
        row = self._session.scalar(
            select(OAuthTransactionModel).where(
                OAuthTransactionModel.state_hash == _hash(opaque_state),
                OAuthTransactionModel.provider == provider,
                OAuthTransactionModel.store_id == store_id,
                OAuthTransactionModel.user_id == user_id,
            )
        )
        if (
            row is None
            or not hmac.compare_digest(row.nonce_hash, _hash(nonce))
            or _aware(row.expires_at) <= datetime.now(UTC)
        ):
            raise AuthenticationError("Expired or mismatched OAuth state")
        return row

    def validate(
        self,
        *,
        state: str,
        provider: str,
        store_id: str,
        user_id: str,
    ) -> OAuthTransactionModel:
        row = self._resolve(
            state=state,
            provider=provider,
            store_id=store_id,
            user_id=user_id,
        )
        if row.used_at is not None:
            raise AuthenticationError("OAuth state was already used")
        return row

    def consume(
        self,
        *,
        state: str,
        provider: str,
        store_id: str,
        user_id: str,
    ) -> OAuthTransactionModel:
        row = self.validate(
            state=state,
            provider=provider,
            store_id=store_id,
            user_id=user_id,
        )
        now = datetime.now(UTC)
        result = cast(
            CursorResult[Any],
            self._session.execute(
                update(OAuthTransactionModel)
                .where(
                    OAuthTransactionModel.id == row.id,
                    OAuthTransactionModel.used_at.is_(None),
                    OAuthTransactionModel.expires_at > now,
                )
                .values(used_at=now)
                .execution_options(synchronize_session=False)
            ),
        )
        if result.rowcount != 1:
            raise AuthenticationError("OAuth state was already used")
        row.used_at = now
        return row

    def store_exchange_result(
        self,
        row: OAuthTransactionModel,
        *,
        credentials: dict[str, str],
        metadata: dict[str, Any],
    ) -> None:
        row.result_credentials_json = encrypt_configured_credentials(credentials)
        row.result_metadata_json = metadata
        self._session.flush()

    def pending_result(
        self,
        *,
        transaction_id: str,
        provider: str,
        store_id: str,
        user_id: str,
    ) -> tuple[OAuthTransactionModel, dict[str, str]]:
        row = self._session.scalar(
            select(OAuthTransactionModel).where(
                OAuthTransactionModel.id == transaction_id,
                OAuthTransactionModel.provider == provider,
                OAuthTransactionModel.store_id == store_id,
                OAuthTransactionModel.user_id == user_id,
            )
        )
        if (
            row is None
            or row.used_at is None
            or row.completed_at is not None
            or _aware(row.expires_at) <= datetime.now(UTC)
        ):
            raise ConflictError("OAuth transaction is unavailable")
        credentials = decrypt_configured_credentials(dict(row.result_credentials_json))
        return row, credentials

    def complete(self, row: OAuthTransactionModel) -> None:
        result = cast(
            CursorResult[Any],
            self._session.execute(
                update(OAuthTransactionModel)
                .where(
                    OAuthTransactionModel.id == row.id,
                    OAuthTransactionModel.completed_at.is_(None),
                )
                .values(completed_at=datetime.now(UTC), result_credentials_json={})
                .execution_options(synchronize_session=False)
            ),
        )
        if result.rowcount != 1:
            raise ConflictError("OAuth transaction was already completed")
