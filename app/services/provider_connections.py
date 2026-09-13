"""Provider connection health, revocation, and secret-safe API projections."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import ChannelModel, ProviderConnectionModel
from app.domain.enums import ProviderConnectionStatus
from app.domain.errors import ExternalProviderError, IntegrationNotConfiguredError
from app.domain.models import ProviderConnectionOut
from app.integrations.commerce import connector_for
from app.repositories.provider_connection_repository import ProviderConnectionRepository


def connection_out(row: ProviderConnectionModel) -> ProviderConnectionOut:
    expires_at = row.token_expires_at
    expiring = False
    if expires_at is not None:
        aware = expires_at.replace(tzinfo=UTC) if expires_at.tzinfo is None else expires_at
        expiring = aware <= datetime.now(UTC) + timedelta(days=7)
    return ProviderConnectionOut(
        id=row.id,
        provider=row.provider,
        connection_type=row.connection_type,
        mode=str(row.metadata_json.get("mode", "live")),
        display_name=row.display_name,
        external_account_id=row.external_account_id,
        external_business_id=row.external_business_id,
        external_resource_id=row.external_resource_id,
        scopes=list(row.scopes_json or []),
        capabilities=list(row.capabilities_json or []),
        status=row.status,
        token_expires_at=expires_at,
        token_expiring=expiring,
        last_health_at=row.last_health_at,
        last_successful_sync_at=row.last_successful_sync_at,
        last_error_code=row.last_error_code,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def list_connections(session: Session, store_id: str) -> list[ProviderConnectionOut]:
    return [
        connection_out(row) for row in ProviderConnectionRepository(session, store_id).list_all()
    ]


def check_connection(
    session: Session,
    settings: Settings,
    store_id: str,
    connection_id: str,
) -> ProviderConnectionOut:
    repository = ProviderConnectionRepository(session, store_id)
    row = repository.get(connection_id)
    credentials = repository.credentials(connection_id)
    commerce_providers = {"shopify", "woocommerce", "generic_website"}
    if row.provider not in {"meta", *commerce_providers}:
        raise IntegrationNotConfiguredError("No health adapter is registered for this provider")
    access_token = credentials.get("access_token", "")
    if row.provider == "meta" and not access_token:
        raise IntegrationNotConfiguredError("Meta access token is unavailable")
    now = datetime.now(UTC)
    if row.metadata_json.get("mode") == "demo":
        row.status = ProviderConnectionStatus.CONNECTED.value
        row.last_health_at = now
        row.last_error_code = None
        row.last_error_message = None
        row.updated_at = now
        session.flush()
        return connection_out(row)
    if row.provider in commerce_providers:
        try:
            connector = connector_for(
                row.provider,
                credentials,
                shopify_api_version=settings.shopify_api_version,
                timeout_seconds=settings.commerce_request_timeout_seconds,
            )
            external_id, provider_name = connector.check_connection()
        except (ExternalProviderError, ValueError):
            row.status = ProviderConnectionStatus.DEGRADED.value
            row.last_error_code = "provider_health_failed"
            row.last_error_message = "Commerce provider health check failed"
        else:
            row.external_account_id = external_id
            row.display_name = row.display_name or provider_name
            row.status = ProviderConnectionStatus.CONNECTED.value
            row.last_error_code = None
            row.last_error_message = None
        row.last_health_at = now
        row.updated_at = now
        session.flush()
        return connection_out(row)
    base = f"{settings.meta_graph_api_base.rstrip('/')}/{settings.meta_graph_api_version}"
    try:
        response = httpx.get(
            f"{base}/{row.external_resource_id}",
            params={"fields": "id,name", "access_token": access_token},
            timeout=settings.meta_request_timeout_seconds,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        row.status = (
            ProviderConnectionStatus.EXPIRED.value
            if status in {400, 401}
            else ProviderConnectionStatus.DEGRADED.value
        )
        row.last_error_code = f"meta_http_{status}"
        row.last_error_message = "Meta connection health check failed"
    except httpx.HTTPError:
        row.status = ProviderConnectionStatus.DEGRADED.value
        row.last_error_code = "meta_unavailable"
        row.last_error_message = "Meta connection health check failed"
    else:
        required_scopes = set(row.metadata_json.get("required_scopes", []))
        missing_scopes = required_scopes - set(row.scopes_json or [])
        if missing_scopes:
            row.status = ProviderConnectionStatus.ACTION_REQUIRED.value
            row.last_error_code = "missing_permissions"
            row.last_error_message = "Provider permissions are incomplete"
        else:
            row.status = ProviderConnectionStatus.CONNECTED.value
            row.last_error_code = None
            row.last_error_message = None
    row.last_health_at = now
    row.updated_at = now
    session.flush()
    return connection_out(row)


def disconnect_connection(
    session: Session,
    settings: Settings,
    store_id: str,
    connection_id: str,
) -> ProviderConnectionOut:
    repository = ProviderConnectionRepository(session, store_id)
    row = repository.get(connection_id)
    credentials = repository.credentials(connection_id)
    is_demo = row.metadata_json.get("mode") == "demo"
    access_token = credentials.get("access_token", "")
    oauth_connection_types = {"facebook_page", "instagram_business"}
    affected_ids = {row.id}
    if row.provider == "meta" and row.connection_type in oauth_connection_types:
        for candidate in repository.list_all():
            if (
                candidate.id != row.id
                and candidate.provider == "meta"
                and candidate.connection_type in oauth_connection_types
                and candidate.status != ProviderConnectionStatus.DISCONNECTED.value
                and repository.credentials(candidate.id).get("access_token") == access_token
            ):
                affected_ids.add(candidate.id)
    if row.provider == "meta" and row.connection_type in oauth_connection_types and not is_demo:
        if not access_token:
            raise IntegrationNotConfiguredError("Meta access token is unavailable")
        base = f"{settings.meta_graph_api_base.rstrip('/')}/{settings.meta_graph_api_version}"
        try:
            response = httpx.delete(
                f"{base}/me/permissions",
                params={"access_token": access_token},
                timeout=settings.meta_request_timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ExternalProviderError(
                "Meta token revocation failed; local credentials were retained"
            ) from exc
    disconnected = row
    for affected_id in affected_ids:
        candidate = repository.disconnect(affected_id)
        if affected_id == connection_id:
            disconnected = candidate
    channels = session.scalars(
        select(ChannelModel).where(
            ChannelModel.store_id == store_id,
            ChannelModel.provider_connection_id.in_(affected_ids),
        )
    ).all()
    for channel in channels:
        channel.is_active = False
        channel.credentials_json = {}
    session.flush()
    return connection_out(disconnected)
