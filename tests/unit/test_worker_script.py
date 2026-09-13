from __future__ import annotations

from http import HTTPStatus

from app.config import Settings
from app.services.job_handlers import REQUIRED_WORKER_JOB_TYPES, load_worker_job_handlers
from scripts.worker import health_response_status, worker_runtime_preflight


def test_worker_ready_endpoint_returns_503_when_not_ready() -> None:
    degraded = {"ready": False}
    assert health_response_status("/health/ready", degraded) == HTTPStatus.SERVICE_UNAVAILABLE
    assert health_response_status("/health/live", degraded) == HTTPStatus.OK
    assert health_response_status("/health", degraded) == HTTPStatus.OK


def test_worker_ready_endpoint_returns_200_when_ready() -> None:
    assert health_response_status("/health/ready", {"ready": True}) == HTTPStatus.OK


def test_standalone_worker_loads_every_durable_job_handler() -> None:
    handlers = load_worker_job_handlers()

    assert handlers.keys() >= REQUIRED_WORKER_JOB_TYPES
    assert handlers["channel.send_message"].__name__ == "deliver_queued_message"


def _production_worker_settings(**overrides: object) -> Settings:
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
        "ai_provider": "deterministic",
        "image_storage_provider": "database",
        "payment_provider": "cod",
        "email_provider": "disabled",
        "cron_secret": "c" * 48,
        "integration_encryption_key": "e" * 48,
        "enable_background_worker": True,
        "meta_oauth_redirect_uri": "https://commerce.example.com/meta/oauth/callback",
    }
    values.update(overrides)
    return Settings(**values)


def test_worker_runtime_preflight_accepts_explicit_persistent_production_worker() -> None:
    settings = _production_worker_settings()

    assert worker_runtime_preflight(settings) == []


def test_worker_runtime_preflight_rejects_disabled_production_worker() -> None:
    settings = _production_worker_settings(enable_background_worker=False)

    assert "ENABLE_BACKGROUND_WORKER must be true" in worker_runtime_preflight(settings)[0]


def test_worker_runtime_preflight_rejects_serverless_worker_runtime() -> None:
    settings = _production_worker_settings(VERCEL=True)

    assert "SERVERLESS_MODE/VERCEL must be false" in worker_runtime_preflight(settings)[0]
