"""Instagram Professional Account container publishing with bounded polling."""

from __future__ import annotations

import time
import uuid
from typing import Protocol

import httpx

from app.config import Settings
from app.domain.enums import Platform
from app.domain.errors import IntegrationNotConfiguredError
from app.domain.models import PublishResult
from app.integrations.facebook import _meta_error, request_with_network_retry


class InstagramPublisher(Protocol):
    def publish(self, image_url: str, caption: str) -> PublishResult: ...

    def check_connection(self) -> bool: ...


class RealInstagramPublisher:
    def __init__(self, settings: Settings):
        self._user_id = settings.instagram_user_id
        self._token = settings.instagram_access_token.get_secret_value()
        self._base = f"{settings.meta_graph_api_base.rstrip('/')}/{settings.meta_graph_api_version}"
        self._interval = settings.meta_poll_interval_seconds
        self._timeout = settings.meta_poll_timeout_seconds
        self._client = httpx.Client(timeout=settings.meta_request_timeout_seconds, trust_env=False)

    def publish(self, image_url: str, caption: str) -> PublishResult:
        if not image_url.startswith("https://"):
            return PublishResult(
                platform=Platform.INSTAGRAM,
                success=False,
                error_code="public_https_image_required",
                error_message="Instagram requires a public HTTPS image URL.",
            )
        creation = self._post(
            f"{self._base}/{self._user_id}/media",
            {"image_url": image_url, "caption": caption, "access_token": self._token},
        )
        creation_id = str(creation["id"])
        status = self._poll_container(creation_id)
        if status != "FINISHED":
            return PublishResult(
                platform=Platform.INSTAGRAM,
                success=False,
                error_code="container_not_ready",
                error_message=f"Instagram container ended with status {status}.",
                raw_status=status,
            )
        published = self._post(
            f"{self._base}/{self._user_id}/media_publish",
            {"creation_id": creation_id, "access_token": self._token},
        )
        media_id = str(published["id"])
        permalink: str | None = None
        detail = request_with_network_retry(
            self._client,
            "GET",
            f"{self._base}/{media_id}",
            params={"fields": "permalink", "access_token": self._token},
        )
        if not detail.is_error:
            permalink = detail.json().get("permalink")
        return PublishResult(
            platform=Platform.INSTAGRAM,
            success=True,
            external_id=media_id,
            permalink=permalink,
            raw_status="PUBLISHED",
        )

    def _post(self, url: str, data: dict[str, str]) -> dict[str, object]:
        response = request_with_network_retry(self._client, "POST", url, data=data)
        if response.is_error:
            raise _meta_error(response)
        return dict(response.json())

    def _poll_container(self, creation_id: str) -> str:
        deadline = time.monotonic() + self._timeout
        last_status = "IN_PROGRESS"
        while time.monotonic() < deadline:
            response = request_with_network_retry(
                self._client,
                "GET",
                f"{self._base}/{creation_id}",
                params={"fields": "status_code,status", "access_token": self._token},
            )
            if response.is_error:
                raise _meta_error(response)
            payload = response.json()
            last_status = str(payload.get("status_code", "UNKNOWN"))
            if last_status in {"FINISHED", "ERROR", "EXPIRED"}:
                return last_status
            time.sleep(self._interval)
        return f"TIMEOUT:{last_status}"

    def check_connection(self) -> bool:
        response = request_with_network_retry(
            self._client,
            "GET",
            f"{self._base}/{self._user_id}",
            params={"fields": "id,username", "access_token": self._token},
        )
        if response.is_error:
            raise _meta_error(response)
        return True


class FakeInstagramPublisher:
    def publish(self, image_url: str, caption: str) -> PublishResult:
        del image_url, caption
        identifier = f"demo-instagram-{uuid.uuid4().hex[:12]}"
        return PublishResult(
            platform=Platform.INSTAGRAM,
            success=True,
            external_id=identifier,
            permalink=f"https://demo.invalid/instagram/{identifier}",
            raw_status="DEMO",
        )

    def check_connection(self) -> bool:
        return True


class DisabledInstagramPublisher:
    def publish(self, image_url: str, caption: str) -> PublishResult:
        del image_url, caption
        return PublishResult(
            platform=Platform.INSTAGRAM,
            success=False,
            error_code="publishing_disabled",
            error_message="Instagram publishing is disabled.",
            raw_status="DISABLED",
        )

    def check_connection(self) -> bool:
        raise IntegrationNotConfiguredError("Instagram publishing is disabled")
