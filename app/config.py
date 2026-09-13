"""Validated application configuration loaded from environment variables."""

from __future__ import annotations

import json
from decimal import Decimal
from email.utils import getaddresses
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import parse_qs, urlparse

from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Single source of configuration for the complete application."""

    app_env: Literal["development", "test", "staging", "production"] = "development"
    demo_mode: bool = False
    app_secret_key: SecretStr = SecretStr("")
    database_url: str = "sqlite:///./data/commerce.db"
    upload_directory: Path = Path("data/uploads")
    chroma_directory: Path = Path("data/chroma")
    public_base_url: str = "http://localhost:8000"
    allowed_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://localhost:8000",
    ]
    serverless_mode: bool = Field(
        default=False,
        validation_alias=AliasChoices("SERVERLESS_MODE", "VERCEL"),
    )
    search_provider: Literal["sql", "chroma"] = "sql"
    database_pool_size: int = Field(default=5, ge=1, le=20)
    database_max_overflow: int = Field(default=5, ge=0, le=40)
    database_pool_recycle_seconds: int = Field(default=300, ge=30, le=3600)

    demo_merchant_email: str = "merchant@example.com"
    demo_merchant_password_hash: SecretStr = SecretStr("")
    demo_store_id: str = "demo-store"

    ai_provider: Literal["deterministic", "openai"] = "deterministic"
    openai_api_key: SecretStr = SecretStr("")
    ai_gateway_api_key: SecretStr = SecretStr("")
    vercel_oidc_token: SecretStr = SecretStr("")
    openai_base_url: str | None = None
    openai_model: str = "gpt-4.1-mini"
    ai_timeout_seconds: float = Field(default=30, gt=0, le=120)
    ai_circuit_failure_threshold: int = Field(default=5, ge=2, le=20)
    ai_circuit_open_seconds: int = Field(default=60, ge=10, le=600)
    ai_input_cost_per_million_usd: Decimal = Field(default=Decimal("0.40"), ge=0)
    ai_output_cost_per_million_usd: Decimal = Field(default=Decimal("1.60"), ge=0)

    image_storage_provider: Literal["local", "database", "cloudinary"] = "local"
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: SecretStr = SecretStr("")
    cloudinary_api_secret: SecretStr = SecretStr("")
    cloudinary_timeout_seconds: float = Field(default=30, gt=0, le=120)
    malware_scanner: Literal["disabled", "clamav"] = "disabled"
    clamav_host: str = "127.0.0.1"
    clamav_port: int = Field(default=3310, ge=1, le=65535)
    malware_scan_timeout_seconds: float = Field(default=10, gt=0, le=60)

    enable_fake_publishing: bool = False
    enable_real_publishing: bool = False
    meta_graph_api_base: str = "https://graph.facebook.com"
    meta_graph_api_version: str = "v25.0"
    meta_app_id: str = ""
    meta_app_secret: SecretStr = SecretStr("")
    meta_whatsapp_config_id: str = ""
    meta_whatsapp_solution_id: str = ""
    meta_oauth_redirect_uri: str = "http://localhost:8000/meta/oauth/callback"
    facebook_page_id: str = ""
    facebook_page_access_token: SecretStr = SecretStr("")
    instagram_user_id: str = ""
    instagram_access_token: SecretStr = SecretStr("")
    meta_request_timeout_seconds: float = Field(default=20, gt=0, le=120)
    meta_poll_interval_seconds: float = Field(default=2, gt=0, le=30)
    meta_poll_timeout_seconds: float = Field(default=60, gt=0, le=300)
    shopify_app_api_key: str = ""
    shopify_app_api_secret: SecretStr = SecretStr("")
    shopify_oauth_redirect_uri: str = "http://localhost:8000/shopify/oauth/callback"
    shopify_oauth_scopes: str = "read_products,read_orders,write_webhooks"
    shopify_api_version: str = "2026-07"
    commerce_request_timeout_seconds: float = Field(default=30, gt=0, le=120)
    run_meta_smoke_tests: bool = False
    run_live_ai_evals: bool = False

    free_access_mode: bool = True
    billing_provider: Literal["disabled", "demo", "stripe"] = "disabled"
    stripe_secret_key: SecretStr = SecretStr("")
    stripe_webhook_secret: SecretStr = SecretStr("")
    stripe_price_starter: str = ""
    stripe_price_growth: str = ""
    stripe_price_pro: str = ""
    stripe_request_timeout_seconds: float = Field(default=30, gt=0, le=120)

    payment_provider: Literal["disabled", "demo", "cod", "stripe"] = "disabled"
    stripe_payment_webhook_secret: SecretStr = SecretStr("")
    email_provider: Literal["disabled", "resend"] = "disabled"
    resend_api_key: SecretStr = SecretStr("")
    email_from: str = ""
    cron_secret: SecretStr = SecretStr("")
    integration_encryption_key: SecretStr = SecretStr("")
    integration_encryption_key_version: int = Field(default=1, ge=1)
    integration_encryption_previous_keys: SecretStr = SecretStr("")

    enable_background_worker: bool = False
    worker_poll_seconds: float = Field(default=2.0, gt=0, le=60)
    worker_lease_seconds: int = Field(default=300, ge=30, le=3600)
    worker_health_port: int = Field(default=8081, ge=1024, le=65535)
    operator_emails: Annotated[list[str], NoDecode] = []

    max_image_bytes: int = Field(default=10 * 1024 * 1024, ge=1024, le=25 * 1024 * 1024)
    max_channel_media_bytes: int = Field(default=16 * 1024 * 1024, ge=1024, le=100 * 1024 * 1024)
    max_customer_message_length: int = Field(default=2000, ge=100, le=10000)
    retrieval_min_score: float = Field(default=0.05, ge=0, le=1)
    session_ttl_seconds: int = Field(default=8 * 60 * 60, ge=300, le=7 * 24 * 60 * 60)
    cookie_secure: bool = False
    sentry_dsn: SecretStr = SecretStr("")
    release_sha: str = ""

    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("operator_emails", mode="before")
    @classmethod
    def parse_operator_emails(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip().lower() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def validate_external_configuration(self) -> Settings:
        if not self.demo_mode:
            demo_features = [
                name
                for name, enabled in {
                    "ENABLE_FAKE_PUBLISHING": self.enable_fake_publishing,
                    "BILLING_PROVIDER=demo": self.billing_provider == "demo",
                    "PAYMENT_PROVIDER=demo": self.payment_provider == "demo",
                }.items()
                if enabled
            ]
            if demo_features:
                raise ValueError(
                    "Demo features require DEMO_MODE=true: " + ", ".join(demo_features)
                )
        if self.app_env == "production":
            self._validate_production()
        request_scoped_gateway = self.uses_vercel_ai_gateway and self.serverless_mode
        if (
            self.ai_provider == "openai"
            and not self.effective_ai_api_key
            and not request_scoped_gateway
        ):
            raise ValueError(
                "OPENAI_API_KEY is required, or use Vercel AI Gateway with "
                "AI_GATEWAY_API_KEY/VERCEL_OIDC_TOKEN"
            )
        if self.image_storage_provider == "cloudinary":
            missing = [
                name
                for name, value in {
                    "CLOUDINARY_CLOUD_NAME": self.cloudinary_cloud_name,
                    "CLOUDINARY_API_KEY": self.cloudinary_api_key.get_secret_value(),
                    "CLOUDINARY_API_SECRET": self.cloudinary_api_secret.get_secret_value(),
                }.items()
                if not value
            ]
            if missing:
                raise ValueError(f"Missing Cloudinary settings: {', '.join(missing)}")
        if self.email_provider == "resend":
            if not all((self.resend_api_key.get_secret_value(), self.email_from)):
                raise ValueError("RESEND_API_KEY and EMAIL_FROM are required for Resend")
            if not self._valid_single_sender_address(self.email_from):
                raise ValueError("EMAIL_FROM must be one valid sender email address")
        if any(
            (
                self.shopify_app_api_key,
                self.shopify_app_api_secret.get_secret_value(),
            )
        ) and not all(
            (
                self.shopify_app_api_key,
                self.shopify_app_api_secret.get_secret_value(),
            )
        ):
            raise ValueError(
                "SHOPIFY_APP_API_KEY and SHOPIFY_APP_API_SECRET are both required for Shopify OAuth"
            )
        return self

    @staticmethod
    def _valid_single_sender_address(value: str) -> bool:
        if any(character in value for character in "\r\n"):
            return False
        addresses = getaddresses([value])
        if len(addresses) != 1:
            return False
        _, address = addresses[0]
        if not address or any(character.isspace() for character in address):
            return False
        local_part, separator, domain = address.partition("@")
        if not separator or not local_part or not domain:
            return False
        if domain.startswith(".") or domain.endswith(".") or "." not in domain:
            return False
        return ".." not in domain and all(domain.split("."))

    def _validate_production(self) -> None:
        errors: list[str] = []
        secret = self.app_secret_key.get_secret_value()
        forbidden_secrets = {
            "",
            "change-me",
            "development-only-secret-change-before-production",
            "test-secret-key-with-enough-entropy",
        }
        if secret in forbidden_secrets or len(secret) < 32:
            errors.append("APP_SECRET_KEY must be a unique production secret of at least 32 chars")
        if self.demo_mode:
            errors.append("DEMO_MODE must be false in production")
        if self.demo_merchant_password_hash.get_secret_value():
            errors.append("DEMO_MERCHANT_PASSWORD_HASH must be empty in production")
        if self.enable_fake_publishing:
            errors.append("ENABLE_FAKE_PUBLISHING must be false in production")
        if any(
            (
                self.facebook_page_id,
                self.facebook_page_access_token.get_secret_value(),
                self.instagram_user_id,
                self.instagram_access_token.get_secret_value(),
            )
        ):
            errors.append("Global merchant Meta credentials are forbidden; use per-store OAuth")
        if not self.cookie_secure:
            errors.append("COOKIE_SECURE must be true in production")
        parsed_public_url = urlparse(self.public_base_url)
        if parsed_public_url.scheme != "https":
            errors.append("PUBLIC_BASE_URL must use HTTPS in production")
        if not self.allowed_origins:
            errors.append("ALLOWED_ORIGINS must contain at least one trusted HTTPS origin")
        for origin in self.allowed_origins:
            parsed_origin = urlparse(origin)
            if origin == "*" or parsed_origin.scheme != "https" or not parsed_origin.netloc:
                errors.append(f"Unsafe production origin: {origin}")
        database = urlparse(self.database_url.replace("postgresql+psycopg", "postgresql", 1))
        if database.scheme not in {"postgres", "postgresql"}:
            errors.append("Production DATABASE_URL must use PostgreSQL")
        ssl_mode = parse_qs(database.query).get("sslmode", [""])[0]
        if ssl_mode not in {"require", "verify-ca", "verify-full"}:
            errors.append("Production DATABASE_URL must enforce TLS with sslmode")
        if errors:
            raise ValueError("Invalid production configuration: " + "; ".join(errors))

    def production_readiness_issues(self) -> list[str]:
        """Return disabled or incomplete production capabilities without blocking core startup."""

        if self.app_env != "production":
            return []
        issues: list[str] = []
        if self.ai_provider != "openai":
            issues.append("AI provider is not configured")
        if not self.free_access_mode:
            if self.billing_provider != "stripe":
                issues.append("SaaS billing is not configured")
            elif not all(
                (
                    self.stripe_secret_key.get_secret_value(),
                    self.stripe_webhook_secret.get_secret_value(),
                    self.stripe_price_starter,
                    self.stripe_price_growth,
                    self.stripe_price_pro,
                )
            ):
                issues.append("Stripe billing credentials or prices are incomplete")
        if self.payment_provider == "disabled":
            issues.append("Customer payment provider is not configured")
        elif self.payment_provider == "stripe" and not all(
            (
                self.stripe_secret_key.get_secret_value(),
                self.stripe_payment_webhook_secret.get_secret_value(),
            )
        ):
            issues.append("Stripe customer payment credentials are incomplete")
        if self.email_provider != "resend" or not all(
            (self.resend_api_key.get_secret_value(), self.email_from)
        ):
            issues.append("Transactional email is not configured")
        if not self.operator_emails:
            issues.append("Operator access allowlist is not configured")
        if len(self.cron_secret.get_secret_value()) < 32:
            issues.append("Cron authentication is not configured")
        if len(self.integration_encryption_key.get_secret_value()) < 32:
            issues.append("Integration credential encryption is not configured")
        if not self.enable_background_worker:
            issues.append("Persistent background worker runtime is not explicitly enabled")
        if not self.sentry_dsn.get_secret_value():
            issues.append("External error monitoring is not configured")
        if not self.release_sha:
            issues.append("Release SHA is not configured")
        if not all((self.meta_app_id, self.meta_app_secret.get_secret_value())):
            issues.append("Meta App credentials are not configured")
        if not self.meta_whatsapp_config_id:
            issues.append("WhatsApp Embedded Signup configuration is not configured")
        if urlparse(self.meta_oauth_redirect_uri).scheme != "https":
            issues.append("Meta OAuth redirect URL is not production-ready")
        if self.shopify_app_api_key and urlparse(self.shopify_oauth_redirect_uri).scheme != "https":
            issues.append("Shopify OAuth redirect URL is not production-ready")
        if self.image_storage_provider == "local":
            issues.append("External or database-backed media storage is not configured")
        if self.malware_scanner == "disabled":
            issues.append("Malware scanning is not configured")
        return issues

    @property
    def uses_vercel_ai_gateway(self) -> bool:
        if not self.openai_base_url:
            return False
        return urlparse(self.openai_base_url).hostname == "ai-gateway.vercel.sh"

    @property
    def effective_ai_api_key(self) -> str:
        direct_key = self.openai_api_key.get_secret_value()
        if direct_key:
            return direct_key
        if not self.uses_vercel_ai_gateway:
            return ""
        return (
            self.ai_gateway_api_key.get_secret_value() or self.vercel_oidc_token.get_secret_value()
        )

    @property
    def integration_keyring(self) -> dict[int, str]:
        """Parse prior vault keys from a secret JSON object keyed by version."""

        raw = self.integration_encryption_previous_keys.get_secret_value().strip()
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("INTEGRATION_ENCRYPTION_PREVIOUS_KEYS must be a JSON object") from exc
        if not isinstance(parsed, dict):
            raise ValueError("INTEGRATION_ENCRYPTION_PREVIOUS_KEYS must be a JSON object")
        keys: dict[int, str] = {}
        for version, key in parsed.items():
            if not str(version).isdigit() or not isinstance(key, str) or len(key) < 32:
                raise ValueError(
                    "Each previous integration key needs a numeric version and 32+ chars"
                )
            keys[int(version)] = key
        return keys

    @property
    def effective_secret_key(self) -> str:
        value = self.app_secret_key.get_secret_value()
        if value:
            return value
        if self.app_env == "production":
            raise ValueError("APP_SECRET_KEY is required")
        return "development-only-secret-change-before-production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(_env_file=".env", _env_file_encoding="utf-8")
