from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from app.api.routes.integrations import _statuses
from app.config import Settings
from app.domain.models import ProviderConnectionOut


def _connection(
    *,
    provider: str,
    connection_type: str,
    status: str = "connected",
) -> ProviderConnectionOut:
    now = datetime.now(UTC)
    return ProviderConnectionOut(
        id=f"{provider}-{connection_type}",
        provider=provider,
        connection_type=connection_type,
        mode="live",
        display_name="Connection",
        external_account_id=None,
        external_business_id=None,
        external_resource_id="resource",
        scopes=[],
        capabilities=[],
        status=status,
        token_expires_at=None,
        token_expiring=False,
        last_health_at=None,
        last_successful_sync_at=None,
        last_error_code=None,
        created_at=now,
        updated_at=now,
    )


def _production_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "app_env": "production",
        "demo_mode": False,
        "app_secret_key": "a" * 48,
        "database_url": (
            "postgresql+psycopg://commerce:runtime-only@localhost/commerce?sslmode=verify-full"
        ),
        "public_base_url": "https://commerce.example.com",
        "allowed_origins": ["https://commerce.example.com"],
        "cookie_secure": True,
    }
    values.update(overrides)
    return Settings(**values)


def test_production_deterministic_ai_status_is_not_configured() -> None:
    settings = _production_settings(ai_provider="deterministic")

    statuses = {item.name: item for item in _statuses(SimpleNamespace(settings=settings))}

    assert statuses["ai"].mode == "deterministic"
    assert statuses["ai"].configured is False


def test_production_openai_gateway_status_accepts_request_scoped_oidc() -> None:
    settings = _production_settings(
        VERCEL=True,
        ai_provider="openai",
        openai_base_url="https://ai-gateway.vercel.sh/v1",
    )

    statuses = {item.name: item for item in _statuses(SimpleNamespace(settings=settings))}

    assert statuses["ai"].mode == "openai"
    assert statuses["ai"].configured is True


def test_production_media_status_matches_storage_runtime_modes() -> None:
    local_settings = _production_settings(image_storage_provider="local")
    local_statuses = {
        item.name: item for item in _statuses(SimpleNamespace(settings=local_settings))
    }
    assert local_statuses["image_storage"].mode == "local"
    assert local_statuses["image_storage"].configured is False

    database_settings = _production_settings(image_storage_provider="database")
    database_statuses = {
        item.name: item for item in _statuses(SimpleNamespace(settings=database_settings))
    }
    assert database_statuses["image_storage"].mode == "database"
    assert database_statuses["image_storage"].configured is True


def test_production_media_status_requires_full_cloudinary_credentials() -> None:
    settings = _production_settings(
        image_storage_provider="cloudinary",
        cloudinary_cloud_name="commerce",
        cloudinary_api_key="runtime-only-cloudinary-key",
        cloudinary_api_secret="runtime-only-cloudinary-secret",
    )

    statuses = {item.name: item for item in _statuses(SimpleNamespace(settings=settings))}

    assert statuses["image_storage"].mode == "cloudinary"
    assert statuses["image_storage"].configured is True


def test_malware_scanner_status_is_visible_and_production_fail_closed() -> None:
    disabled_settings = _production_settings(malware_scanner="disabled")
    disabled_statuses = {
        item.name: item for item in _statuses(SimpleNamespace(settings=disabled_settings))
    }
    assert disabled_statuses["malware_scanner"].mode == "disabled"
    assert disabled_statuses["malware_scanner"].configured is False

    clamav_settings = _production_settings(malware_scanner="clamav")
    clamav_statuses = {
        item.name: item for item in _statuses(SimpleNamespace(settings=clamav_settings))
    }
    assert clamav_statuses["malware_scanner"].mode == "clamav"
    assert clamav_statuses["malware_scanner"].configured is True


def test_store_connection_statuses_are_secret_safe_summaries() -> None:
    settings = _production_settings()
    statuses = {
        item.name: item
        for item in _statuses(
            SimpleNamespace(settings=settings),
            connections=[
                _connection(provider="meta", connection_type="facebook_page"),
                _connection(
                    provider="meta",
                    connection_type="instagram_business",
                    status="action_required",
                ),
                _connection(provider="shopify", connection_type="store"),
            ],
        )
    }

    assert statuses["meta_social_connections"].configured is True
    assert statuses["meta_social_connections"].mode == "action_required"
    assert statuses["meta_social_connections"].masked_identifier == "1/2 connected"
    assert statuses["commerce_connectors"].configured is True
    assert statuses["commerce_connectors"].mode == "connected"
    assert statuses["commerce_connectors"].masked_identifier == "1/1 connected"


def test_missing_store_connections_are_reported_as_disconnected() -> None:
    settings = _production_settings()
    statuses = {
        item.name: item for item in _statuses(SimpleNamespace(settings=settings), connections=[])
    }

    assert statuses["meta_social_connections"].configured is False
    assert statuses["meta_social_connections"].mode == "disconnected"
    assert statuses["meta_social_connections"].masked_identifier is None
    assert statuses["commerce_connectors"].configured is False
    assert statuses["commerce_connectors"].mode == "disconnected"
    assert statuses["commerce_connectors"].masked_identifier is None
