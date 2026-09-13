"""Per-store Facebook and Instagram publishing using encrypted OAuth connections."""

from __future__ import annotations

import time
from contextlib import suppress
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import ProviderConnectionModel
from app.domain.enums import Platform, ProviderConnectionStatus
from app.domain.errors import ConflictError
from app.domain.models import PublishResult
from app.repositories.provider_connection_repository import ProviderConnectionRepository


class StoreMetaPublisher:
    def __init__(
        self,
        session: Session,
        settings: Settings,
        store_id: str,
        platform: Platform,
    ):
        self._session = session
        self._settings = settings
        self._store_id = store_id
        self._platform = platform

    def _connection(self) -> tuple[ProviderConnectionModel, dict[str, str]]:
        connection_type = (
            "facebook_page" if self._platform == Platform.FACEBOOK else "instagram_business"
        )
        row = self._session.scalar(
            select(ProviderConnectionModel)
            .where(
                ProviderConnectionModel.store_id == self._store_id,
                ProviderConnectionModel.provider == "meta",
                ProviderConnectionModel.connection_type == connection_type,
                ProviderConnectionModel.status == ProviderConnectionStatus.CONNECTED.value,
            )
            .order_by(ProviderConnectionModel.updated_at.desc())
        )
        if row is None:
            raise ConflictError(
                "No healthy Meta publishing connection for this store",
                details={"platform": self._platform.value},
            )
        credentials = ProviderConnectionRepository(self._session, self._store_id).credentials(
            row.id
        )
        return row, credentials

    def _request(
        self,
        method: str,
        path: str,
        *,
        token: str,
        data: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        base = (
            f"{self._settings.meta_graph_api_base.rstrip('/')}/"
            f"{self._settings.meta_graph_api_version}"
        )
        try:
            response = httpx.request(
                method,
                f"{base}/{path.lstrip('/')}",
                data=data,
                params=params,
                headers={"Authorization": f"Bearer {token}"},
                timeout=self._settings.meta_request_timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
            return dict(body) if isinstance(body, dict) else {}
        except (httpx.HTTPError, ValueError) as exc:
            code = "meta_provider_error"
            if isinstance(exc, httpx.HTTPStatusError):
                with suppress(ValueError, AttributeError):
                    code = str(exc.response.json().get("error", {}).get("code", code))
            raise ConflictError(
                "Meta publishing failed",
                details={"platform": self._platform.value, "provider_code": code},
            ) from exc

    def publish(self, image_url: str, message: str) -> PublishResult:
        row, credentials = self._connection()
        token = credentials.get("access_token", "")
        account_id = credentials.get("account_id") or row.external_resource_id
        if not token or not account_id:
            raise ConflictError("Meta publishing credentials are incomplete")
        if self._platform == Platform.FACEBOOK:
            created = self._request(
                "POST",
                f"{account_id}/photos",
                token=token,
                data={"url": image_url, "caption": message, "published": "true"},
            )
            external_id = str(created.get("post_id") or created.get("id") or "")
            return PublishResult(
                platform=self._platform,
                success=True,
                external_id=external_id or None,
                raw_status="PUBLISHED",
            )
        if not image_url.startswith("https://"):
            return PublishResult(
                platform=self._platform,
                success=False,
                error_code="public_https_image_required",
                error_message="Instagram requires a public HTTPS image URL.",
            )
        container = self._request(
            "POST",
            f"{account_id}/media",
            token=token,
            data={"image_url": image_url, "caption": message},
        )
        container_id = str(container.get("id", ""))
        deadline = time.monotonic() + self._settings.meta_poll_timeout_seconds
        status = "IN_PROGRESS"
        while time.monotonic() < deadline:
            detail = self._request(
                "GET",
                container_id,
                token=token,
                params={"fields": "status_code"},
            )
            status = str(detail.get("status_code", "UNKNOWN"))
            if status in {"FINISHED", "ERROR", "EXPIRED"}:
                break
            time.sleep(self._settings.meta_poll_interval_seconds)
        if status != "FINISHED":
            return PublishResult(
                platform=self._platform,
                success=False,
                error_code="container_not_ready",
                error_message=f"Instagram container ended with status {status}.",
                raw_status=status,
            )
        published = self._request(
            "POST",
            f"{account_id}/media_publish",
            token=token,
            data={"creation_id": container_id},
        )
        media_id = str(published.get("id", ""))
        detail = self._request(
            "GET",
            media_id,
            token=token,
            params={"fields": "permalink"},
        )
        return PublishResult(
            platform=self._platform,
            success=True,
            external_id=media_id or None,
            permalink=str(detail.get("permalink", "")) or None,
            raw_status="PUBLISHED",
        )

    def check_connection(self) -> bool:
        row, credentials = self._connection()
        account_id = credentials.get("account_id") or row.external_resource_id
        self._request(
            "GET",
            account_id,
            token=credentials.get("access_token", ""),
            params={"fields": "id,name,username"},
        )
        return True
