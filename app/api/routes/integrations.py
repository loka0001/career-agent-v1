"""Secret-safe integration status and connection checks."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter

from app.api.dependencies import (
    AdminUser,
    ContainerDependency,
    CurrentUser,
    DatabaseDependency,
)
from app.api.schemas import IntegrationStatusResponse
from app.domain.models import IntegrationStatus, ProviderConnectionOut
from app.services.provider_connections import (
    check_connection,
    disconnect_connection,
    list_connections,
)

router = APIRouter(prefix="/integrations", tags=["integrations"])

_COMMERCE_PROVIDERS = {"shopify", "woocommerce", "generic_website"}
_META_SOCIAL_CONNECTION_TYPES = {"facebook_page", "instagram_business"}
_ATTENTION_STATUSES = {"action_required", "degraded", "expired"}


def _mask(value: str) -> str | None:
    if not value:
        return None
    if len(value) <= 4:
        return "*" * len(value)
    return f"{'*' * (len(value) - 4)}{value[-4:]}"


def _connection_summary_mode(connections: list[ProviderConnectionOut]) -> str:
    if not connections:
        return "disconnected"
    statuses = {connection.status for connection in connections}
    if statuses == {"connected"}:
        return "connected"
    if statuses & _ATTENTION_STATUSES:
        return "action_required"
    if "connected" in statuses:
        return "partial"
    if statuses == {"disconnected"}:
        return "disconnected"
    return "pending"


def _connection_summary(
    name: str,
    connections: list[ProviderConnectionOut],
    *,
    checked: bool,
) -> IntegrationStatus:
    connected = sum(1 for connection in connections if connection.status == "connected")
    total = len(connections)
    return IntegrationStatus(
        name=name,
        configured=connected > 0,
        mode=_connection_summary_mode(connections),
        masked_identifier=f"{connected}/{total} connected" if total else None,
        last_check=datetime.now(UTC) if checked and total else None,
    )


def _statuses(
    container: ContainerDependency,
    *,
    checked: bool = False,
    connections: list[ProviderConnectionOut] | None = None,
) -> list[IntegrationStatus]:
    settings = container.settings
    now = datetime.now(UTC) if checked else None
    if settings.enable_real_publishing:
        publishing_mode = "real"
    elif settings.enable_fake_publishing:
        publishing_mode = "demo"
    else:
        publishing_mode = "disabled"
    if settings.ai_provider == "openai":
        ai_configured = bool(settings.effective_ai_api_key) or (
            settings.uses_vercel_ai_gateway and settings.serverless_mode
        )
    else:
        ai_configured = settings.ai_provider == "deterministic" and settings.app_env != "production"
    if settings.image_storage_provider == "database":
        image_storage_configured = True
    elif settings.image_storage_provider == "cloudinary":
        image_storage_configured = all(
            (
                settings.cloudinary_cloud_name,
                settings.cloudinary_api_key.get_secret_value(),
                settings.cloudinary_api_secret.get_secret_value(),
            )
        )
    else:
        image_storage_configured = settings.app_env != "production"
    malware_configured = settings.malware_scanner == "clamav" or settings.app_env != "production"
    statuses = [
        IntegrationStatus(
            name="ai",
            configured=ai_configured,
            mode=settings.ai_provider,
            last_check=now,
        ),
        IntegrationStatus(
            name="image_storage",
            configured=image_storage_configured,
            mode=settings.image_storage_provider,
            last_check=now,
        ),
        IntegrationStatus(
            name="malware_scanner",
            configured=malware_configured,
            mode=settings.malware_scanner,
            last_check=now,
        ),
        IntegrationStatus(
            name="facebook",
            configured=settings.enable_fake_publishing
            or bool(settings.facebook_page_access_token.get_secret_value()),
            mode=publishing_mode,
            masked_identifier=_mask(settings.facebook_page_id),
            last_check=now,
        ),
        IntegrationStatus(
            name="instagram",
            configured=settings.enable_fake_publishing
            or bool(settings.instagram_access_token.get_secret_value()),
            mode=publishing_mode,
            masked_identifier=_mask(settings.instagram_user_id),
            last_check=now,
        ),
    ]
    if connections is not None:
        meta_social = [
            connection
            for connection in connections
            if connection.provider == "meta"
            and connection.connection_type in _META_SOCIAL_CONNECTION_TYPES
        ]
        commerce = [
            connection for connection in connections if connection.provider in _COMMERCE_PROVIDERS
        ]
        statuses.extend(
            (
                _connection_summary(
                    "meta_social_connections",
                    meta_social,
                    checked=checked,
                ),
                _connection_summary(
                    "commerce_connectors",
                    commerce,
                    checked=checked,
                ),
            )
        )
    return statuses


@router.get("", response_model=IntegrationStatusResponse)
def integration_status(
    user: CurrentUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> IntegrationStatusResponse:
    connections = list_connections(db, user.store_id)
    return IntegrationStatusResponse(integrations=_statuses(container, connections=connections))


@router.post("/meta/check", response_model=IntegrationStatusResponse)
def check_meta(
    user: AdminUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> IntegrationStatusResponse:
    connections = list_connections(db, user.store_id)
    meta_connections = [
        connection
        for connection in connections
        if connection.provider == "meta"
        and connection.connection_type in _META_SOCIAL_CONNECTION_TYPES
        and connection.status != "disconnected"
    ]
    if meta_connections:
        for connection in meta_connections:
            check_connection(db, container.settings, user.store_id, connection.id)
        connections = list_connections(db, user.store_id)
    elif (container.settings.demo_mode and container.settings.enable_fake_publishing) or any(
        (
            container.settings.facebook_page_access_token.get_secret_value(),
            container.settings.instagram_access_token.get_secret_value(),
        )
    ):
        container.facebook_publisher.check_connection()
        container.instagram_publisher.check_connection()
    return IntegrationStatusResponse(
        integrations=_statuses(container, checked=True, connections=connections)
    )


@router.get("/connections", response_model=list[ProviderConnectionOut])
def connections(user: CurrentUser, db: DatabaseDependency) -> list[ProviderConnectionOut]:
    return list_connections(db, user.store_id)


@router.post("/connections/{connection_id}/check", response_model=ProviderConnectionOut)
def check_provider_connection(
    connection_id: str,
    user: AdminUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> ProviderConnectionOut:
    return check_connection(db, container.settings, user.store_id, connection_id)


@router.post(
    "/connections/{connection_id}/disconnect",
    response_model=ProviderConnectionOut,
)
def disconnect_provider_connection(
    connection_id: str,
    user: AdminUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> ProviderConnectionOut:
    return disconnect_connection(
        db,
        container.settings,
        user.store_id,
        connection_id,
    )
