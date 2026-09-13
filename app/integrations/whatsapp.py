"""WhatsApp Business Cloud API adapter."""

from __future__ import annotations

import logging
from contextlib import suppress
from typing import Any
from urllib.parse import urlparse

import httpx

from app.domain.errors import ExternalProviderError, InvalidInputError
from app.domain.models import SendResult

logger = logging.getLogger(__name__)


class WhatsAppCloudAdapter:
    def __init__(self, graph_api_base: str, graph_api_version: str, timeout_seconds: float):
        self._base = graph_api_base.rstrip("/")
        self._version = graph_api_version
        self._timeout = timeout_seconds

    def _post(self, credentials: dict[str, Any], payload: dict[str, Any]) -> SendResult:
        token = str(credentials.get("access_token", ""))
        phone_number_id = str(credentials.get("phone_number_id", ""))
        if not token or not phone_number_id:
            return SendResult(
                success=False,
                error_code="not_configured",
                error_message="WhatsApp credentials are incomplete",
            )
        try:
            response = httpx.post(
                f"{self._base}/{self._version}/{phone_number_id}/messages",
                headers={"Authorization": f"Bearer {token}"},
                json={"messaging_product": "whatsapp", **payload},
                timeout=self._timeout,
            )
            response.raise_for_status()
            data = response.json()
            messages = data.get("messages", [])
            external_id = str(messages[0].get("id", "")) if messages else None
            return SendResult(success=True, external_id=external_id)
        except httpx.HTTPStatusError as exc:
            code = f"http_{exc.response.status_code}"
            message = "WhatsApp rejected the request"
            try:
                error = exc.response.json().get("error", {})
                code = str(error.get("code", code))
                message = str(error.get("message", message))
            except (ValueError, AttributeError):
                pass
            logger.warning("whatsapp_api_error", extra={"provider_code": code})
            return SendResult(success=False, error_code=code, error_message=message[:500])
        except httpx.HTTPError:
            logger.warning("whatsapp_transport_error")
            return SendResult(
                success=False,
                error_code="transport_error",
                error_message="WhatsApp could not be reached",
            )

    def send_text(
        self, credentials: dict[str, Any], recipient_external_id: str, text: str
    ) -> SendResult:
        return self._post(
            credentials,
            {
                "to": recipient_external_id,
                "type": "text",
                "text": {"preview_url": False, "body": text},
            },
        )

    def send_template(
        self,
        credentials: dict[str, Any],
        recipient_external_id: str,
        name: str,
        language: str,
        parameters: list[str],
    ) -> SendResult:
        components: list[dict[str, Any]] = []
        if parameters:
            components.append(
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": parameter} for parameter in parameters],
                }
            )
        return self._post(
            credentials,
            {
                "to": recipient_external_id,
                "type": "template",
                "template": {
                    "name": name,
                    "language": {"code": language},
                    "components": components,
                },
            },
        )

    def send_media(
        self,
        credentials: dict[str, Any],
        recipient_external_id: str,
        media_type: str,
        url: str,
        caption: str,
        filename: str | None,
    ) -> SendResult:
        if media_type not in {"image", "document", "audio"}:
            return SendResult(
                success=False,
                error_code="unsupported_media",
                error_message="Unsupported WhatsApp media type",
            )
        media: dict[str, Any] = {"link": url}
        if caption and media_type in {"image", "document"}:
            media["caption"] = caption
        if filename and media_type == "document":
            media["filename"] = filename
        return self._post(
            credentials,
            {
                "to": recipient_external_id,
                "type": media_type,
                media_type: media,
            },
        )

    def check_connection(self, credentials: dict[str, Any]) -> tuple[bool, str | None]:
        token = str(credentials.get("access_token", ""))
        phone_number_id = str(credentials.get("phone_number_id", ""))
        if not token or not phone_number_id:
            return False, "not_configured"
        try:
            response = httpx.get(
                f"{self._base}/{self._version}/{phone_number_id}",
                headers={"Authorization": f"Bearer {token}"},
                params={"fields": "id,display_phone_number,verified_name"},
                timeout=self._timeout,
            )
            response.raise_for_status()
            return True, None
        except httpx.HTTPStatusError as exc:
            return False, f"http_{exc.response.status_code}"
        except httpx.HTTPError:
            return False, "transport_error"


class WhatsAppManagementClient:
    """Business-management operations used after Embedded Signup."""

    def __init__(self, graph_api_base: str, graph_api_version: str, timeout_seconds: float):
        self._root = graph_api_base.rstrip("/")
        self._base = f"{self._root}/{graph_api_version}"
        self._timeout = timeout_seconds

    def _request(
        self,
        method: str,
        url: str,
        *,
        token: str,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            response = httpx.request(
                method,
                url,
                headers={"Authorization": f"Bearer {token}"} if token else {},
                params=params,
                json=json,
                timeout=self._timeout,
            )
            response.raise_for_status()
            body = response.json()
            if not isinstance(body, dict):
                raise ValueError("Provider response is not an object")
            return dict(body)
        except (httpx.HTTPError, ValueError) as exc:
            code = "provider_error"
            if isinstance(exc, httpx.HTTPStatusError):
                with suppress(ValueError, AttributeError):
                    code = str(exc.response.json().get("error", {}).get("code", code))
            raise ExternalProviderError(
                "WhatsApp management request failed",
                details={"provider_code": code},
            ) from exc

    def exchange_code(self, code: str, app_id: str, app_secret: str) -> str:
        result = self._request(
            "GET",
            f"{self._root}/oauth/access_token",
            token="",
            params={
                "client_id": app_id,
                "client_secret": app_secret,
                "code": code,
            },
        )
        token = str(result.get("access_token", ""))
        if not token:
            raise ExternalProviderError("Meta did not return an access token")
        return token

    def discover_waba_ids(self, access_token: str, app_id: str, app_secret: str) -> list[str]:
        result = self._request(
            "GET",
            f"{self._root}/debug_token",
            token="",
            params={
                "input_token": access_token,
                "access_token": f"{app_id}|{app_secret}",
            },
        )
        data = result.get("data", {})
        if not isinstance(data, dict) or not data.get("is_valid"):
            raise ExternalProviderError("Embedded Signup returned an invalid token")
        ids: set[str] = set()
        for scope in data.get("granular_scopes", []):
            if isinstance(scope, dict) and scope.get("scope") == "whatsapp_business_management":
                ids.update(str(value) for value in scope.get("target_ids", []) if value)
        return sorted(ids)

    def list_phone_numbers(self, access_token: str, waba_id: str) -> list[dict[str, str]]:
        result = self._request(
            "GET",
            f"{self._base}/{waba_id}/phone_numbers",
            token=access_token,
            params={
                "fields": (
                    "id,display_phone_number,verified_name,quality_rating,"
                    "code_verification_status,platform_type"
                )
            },
        )
        phones: list[dict[str, str]] = []
        for item in result.get("data", []):
            if isinstance(item, dict) and item.get("id"):
                phones.append(
                    {
                        "phone_number_id": str(item["id"]),
                        "waba_id": waba_id,
                        "display_phone_number": str(item.get("display_phone_number", "")),
                        "verified_name": str(item.get("verified_name", "")),
                        "quality_rating": str(item.get("quality_rating", "")),
                        "verification_status": str(item.get("code_verification_status", "")),
                    }
                )
        return phones

    def subscribe_app(self, access_token: str, waba_id: str) -> None:
        self._request(
            "POST",
            f"{self._base}/{waba_id}/subscribed_apps",
            token=access_token,
        )

    def register_phone(self, access_token: str, phone_number_id: str, pin: str | None) -> None:
        payload: dict[str, Any] = {"messaging_product": "whatsapp"}
        if pin:
            payload["pin"] = pin
        self._request(
            "POST",
            f"{self._base}/{phone_number_id}/register",
            token=access_token,
            json=payload,
        )

    def create_template(
        self,
        access_token: str,
        waba_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"{self._base}/{waba_id}/message_templates",
            token=access_token,
            json=payload,
        )

    def list_templates(self, access_token: str, waba_id: str) -> list[dict[str, Any]]:
        result = self._request(
            "GET",
            f"{self._base}/{waba_id}/message_templates",
            token=access_token,
            params={
                "fields": (
                    "id,name,language,status,category,components,rejected_reason,quality_score"
                ),
                "limit": "250",
            },
        )
        return [dict(item) for item in result.get("data", []) if isinstance(item, dict)]

    def download_media(
        self,
        access_token: str,
        media_id: str,
        max_bytes: int,
    ) -> tuple[bytes, str]:
        metadata = self._request(
            "GET",
            f"{self._base}/{media_id}",
            token=access_token,
        )
        url = str(metadata.get("url", ""))
        parsed = urlparse(url)
        allowed_hosts = ("facebook.com", "fbcdn.net", "fbsbx.com")
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or not any(
                parsed.hostname == host or parsed.hostname.endswith(f".{host}")
                for host in allowed_hosts
            )
        ):
            raise InvalidInputError("Meta returned an unsafe media URL")
        try:
            response = httpx.get(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=self._timeout,
                follow_redirects=False,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ExternalProviderError("WhatsApp media download failed") from exc
        if len(response.content) > max_bytes:
            raise InvalidInputError("WhatsApp media exceeds the configured size limit")
        mime_type = response.headers.get(
            "Content-Type", str(metadata.get("mime_type", "application/octet-stream"))
        ).split(";", 1)[0]
        return response.content, mime_type
