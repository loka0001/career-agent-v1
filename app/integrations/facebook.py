"""Facebook Page photo publishing adapter for Graph API v25.0."""

from __future__ import annotations

import time
import uuid
from typing import Any, Protocol

import httpx

from app.config import Settings
from app.domain.enums import Platform
from app.domain.errors import ExternalProviderError, IntegrationNotConfiguredError
from app.domain.models import PublishResult


class FacebookPublisher(Protocol):
    def publish(self, image_url: str, message: str) -> PublishResult: ...

    def check_connection(self) -> bool: ...


def request_with_network_retry(
    client: httpx.Client, method: str, url: str, **kwargs: Any
) -> httpx.Response:
    """Retry one transport failure only for safe, read-only HTTP methods."""

    attempts = 2 if method.upper() in {"GET", "HEAD", "OPTIONS"} else 1
    for attempt in range(attempts):
        try:
            return client.request(method, url, **kwargs)
        except httpx.HTTPError as exc:
            if attempt == attempts - 1:
                raise ExternalProviderError("Meta network error") from exc
            time.sleep(0.2)
    raise ExternalProviderError("Meta network error")


def _meta_error(response: httpx.Response) -> ExternalProviderError:
    try:
        error = response.json().get("error", {})
    except ValueError:
        error = {}
    code = str(error.get("code", response.status_code))
    category = "meta_error"
    if code in {"10", "190", "200"}:
        category = "permission_or_token_error"
    elif code in {"4", "17", "32", "613"}:
        category = "rate_limit"
    elif code in {"100", "36005"}:
        category = "invalid_image_or_parameter"
    return ExternalProviderError(category, details={"provider_code": code})


class RealFacebookPublisher:
    def __init__(self, settings: Settings):
        self._page_id = settings.facebook_page_id
        self._token = settings.facebook_page_access_token.get_secret_value()
        self._base = f"{settings.meta_graph_api_base.rstrip('/')}/{settings.meta_graph_api_version}"
        self._client = httpx.Client(timeout=settings.meta_request_timeout_seconds, trust_env=False)

    def publish(self, image_url: str, message: str) -> PublishResult:
        if not image_url.startswith("https://"):
            return PublishResult(
                platform=Platform.FACEBOOK,
                success=False,
                error_code="public_https_image_required",
                error_message="Facebook requires a public HTTPS image URL.",
            )
        response = request_with_network_retry(
            self._client,
            "POST",
            f"{self._base}/{self._page_id}/photos",
            data={"url": image_url, "message": message, "access_token": self._token},
        )
        if response.is_error:
            raise _meta_error(response)
        payload = response.json()
        external_id = str(payload.get("post_id") or payload.get("id"))
        permalink: str | None = None
        detail = request_with_network_retry(
            self._client,
            "GET",
            f"{self._base}/{external_id}",
            params={"fields": "permalink_url", "access_token": self._token},
        )
        if not detail.is_error:
            permalink = detail.json().get("permalink_url")
        return PublishResult(
            platform=Platform.FACEBOOK,
            success=True,
            external_id=external_id,
            permalink=permalink,
            raw_status="PUBLISHED",
        )

    def check_connection(self) -> bool:
        response = request_with_network_retry(
            self._client,
            "GET",
            f"{self._base}/{self._page_id}",
            params={"fields": "id,name", "access_token": self._token},
        )
        if response.is_error:
            raise _meta_error(response)
        return True


class FakeFacebookPublisher:
    def publish(self, image_url: str, message: str) -> PublishResult:
        del image_url, message
        identifier = f"demo-facebook-{uuid.uuid4().hex[:12]}"
        return PublishResult(
            platform=Platform.FACEBOOK,
            success=True,
            external_id=identifier,
            permalink=f"https://demo.invalid/facebook/{identifier}",
            raw_status="DEMO",
        )

    def check_connection(self) -> bool:
        return True


class DisabledFacebookPublisher:
    def publish(self, image_url: str, message: str) -> PublishResult:
        del image_url, message
        return PublishResult(
            platform=Platform.FACEBOOK,
            success=False,
            error_code="publishing_disabled",
            error_message="Facebook publishing is disabled.",
            raw_status="DISABLED",
        )

    def check_connection(self) -> bool:
        raise IntegrationNotConfiguredError("Facebook publishing is disabled")
