from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import Settings


def _production_settings(**overrides: object) -> dict[str, object]:
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
        "ai_provider": "openai",
        "openai_api_key": "runtime-only-openai-key",
        "image_storage_provider": "cloudinary",
        "cloudinary_cloud_name": "commerce",
        "cloudinary_api_key": "runtime-only-cloudinary-key",
        "cloudinary_api_secret": "runtime-only-cloudinary-secret",
        "enable_fake_publishing": False,
        "free_access_mode": False,
        "billing_provider": "stripe",
        "stripe_secret_key": "runtime-only-stripe-secret",
        "stripe_webhook_secret": "runtime-only-stripe-webhook",
        "stripe_price_starter": "price_starter",
        "stripe_price_growth": "price_growth",
        "stripe_price_pro": "price_pro",
        "payment_provider": "cod",
        "email_provider": "resend",
        "resend_api_key": "runtime-only-resend-key",
        "email_from": "Commerce <system@example.com>",
        "cron_secret": "c" * 48,
        "integration_encryption_key": "e" * 48,
        "enable_background_worker": True,
        "operator_emails": ["ops@example.com"],
        "sentry_dsn": "https://public@example.com/1",
        "release_sha": "0123456789abcdef",
        "meta_app_id": "123456",
        "meta_app_secret": "runtime-only-meta-secret",
        "meta_whatsapp_config_id": "whatsapp_config",
        "meta_oauth_redirect_uri": "https://commerce.example.com/meta/oauth/callback",
        "malware_scanner": "clamav",
    }
    values.update(overrides)
    return values


def test_valid_production_configuration_is_accepted() -> None:
    settings = Settings(**_production_settings())
    assert settings.app_env == "production"


def test_explicit_settings_are_not_polluted_by_local_dotenv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".env").write_text(
        "DEMO_MODE=true\nENABLE_FAKE_PUBLISHING=true\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    settings = Settings(
        app_env="test",
        demo_mode=False,
        app_secret_key="test-secret-key-with-enough-entropy",
        database_url="sqlite://",
        ai_provider="deterministic",
    )

    assert settings.demo_mode is False
    assert settings.enable_fake_publishing is False
    assert settings.demo_mode is False
    assert settings.production_readiness_issues() == []


@pytest.mark.parametrize(
    "email_from",
    [
        "missing-domain",
        "Commerce <system@localhost>",
        "Commerce <system@example.com>, Ops <ops@example.com>",
        "Commerce <system@example.com>\r\nBcc: attacker@example.com",
    ],
)
def test_resend_requires_one_safe_sender_address(email_from: str) -> None:
    with pytest.raises(ValidationError, match="EMAIL_FROM"):
        Settings(**_production_settings(email_from=email_from))


def test_shopify_oauth_requires_complete_app_credentials() -> None:
    with pytest.raises(ValidationError, match="SHOPIFY_APP_API_KEY"):
        Settings(shopify_app_api_key="shopify-app-key")
    with pytest.raises(ValidationError, match="SHOPIFY_APP_API_KEY"):
        Settings(shopify_app_api_secret="runtime-only-shopify-secret")


def test_shopify_oauth_redirect_warning_is_production_only_when_configured() -> None:
    settings = Settings(
        **_production_settings(
            shopify_app_api_key="shopify-app-key",
            shopify_app_api_secret="runtime-only-shopify-secret",
            shopify_oauth_redirect_uri="http://localhost/shopify/oauth/callback",
        )
    )

    assert "Shopify OAuth redirect URL is not production-ready" in (
        settings.production_readiness_issues()
    )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("demo_mode", True, "DEMO_MODE"),
        ("enable_fake_publishing", True, "Demo features require"),
        ("database_url", "sqlite:///commerce.db", "PostgreSQL"),
        (
            "database_url",
            "postgresql://commerce:runtime-only@localhost/commerce",
            "sslmode",
        ),
        ("cookie_secure", False, "COOKIE_SECURE"),
        ("allowed_origins", ["*"], "Unsafe production origin"),
        ("payment_provider", "demo", "Demo features require"),
    ],
)
def test_unsafe_production_configuration_is_rejected(
    field: str, value: object, message: str
) -> None:
    values = _production_settings(**{field: value})
    with pytest.raises(ValidationError, match=message):
        Settings(**values)


def test_incomplete_optional_providers_do_not_block_core_startup() -> None:
    settings = Settings(
        **_production_settings(
            ai_provider="deterministic",
            openai_api_key="",
            billing_provider="disabled",
            payment_provider="disabled",
            email_provider="disabled",
            resend_api_key="",
            email_from="",
            cron_secret="",
            integration_encryption_key="",
            operator_emails=[],
            sentry_dsn="",
            release_sha="",
            meta_app_id="",
            meta_app_secret="",
            meta_oauth_redirect_uri="http://localhost/meta/callback",
            image_storage_provider="database",
            cloudinary_cloud_name="",
            cloudinary_api_key="",
            cloudinary_api_secret="",
        )
    )

    issues = settings.production_readiness_issues()
    assert "AI provider is not configured" in issues
    assert "SaaS billing is not configured" in issues
    assert "Operator access allowlist is not configured" in issues
    assert "External error monitoring is not configured" in issues
    assert "Release SHA is not configured" in issues
    assert "Meta App credentials are not configured" in issues


def test_free_access_does_not_require_stripe_billing() -> None:
    settings = Settings(**_production_settings(free_access_mode=True, billing_provider="disabled"))
    issues = settings.production_readiness_issues()
    assert "SaaS billing is not configured" not in issues
    assert "Stripe billing credentials or prices are incomplete" not in issues


def test_vercel_ai_gateway_accepts_automatic_oidc_token() -> None:
    settings = Settings(
        app_env="test",
        demo_mode=False,
        app_secret_key="test-secret-key-with-enough-entropy",
        database_url="sqlite://",
        ai_provider="openai",
        openai_base_url="https://ai-gateway.vercel.sh/v1",
        vercel_oidc_token="automatic-vercel-oidc-token",
    )

    assert settings.uses_vercel_ai_gateway is True
    assert settings.effective_ai_api_key == "automatic-vercel-oidc-token"


def test_serverless_vercel_ai_gateway_accepts_request_scoped_oidc() -> None:
    settings = Settings(
        app_env="test",
        demo_mode=False,
        app_secret_key="test-secret-key-with-enough-entropy",
        database_url="sqlite://",
        VERCEL=True,
        ai_provider="openai",
        openai_base_url="https://ai-gateway.vercel.sh/v1",
    )

    assert settings.effective_ai_api_key == ""
    assert settings.uses_vercel_ai_gateway is True


def test_oidc_token_is_not_accepted_for_an_arbitrary_openai_base_url() -> None:
    with pytest.raises(ValidationError, match="OPENAI_API_KEY"):
        Settings(
            app_env="test",
            demo_mode=False,
            app_secret_key="test-secret-key-with-enough-entropy",
            database_url="sqlite://",
            ai_provider="openai",
            openai_base_url="https://untrusted.example/v1",
            vercel_oidc_token="automatic-vercel-oidc-token",
        )
