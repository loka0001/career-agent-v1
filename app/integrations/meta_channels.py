"""Meta messaging and comment adapters behind the channel seam."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.domain.enums import ChannelType
from app.domain.models import SendResult

logger = logging.getLogger(__name__)


class MetaChannelAdapter:
    def __init__(
        self,
        channel_type: ChannelType,
        graph_api_base: str,
        graph_api_version: str,
        timeout_seconds: float,
    ):
        self._channel_type = channel_type
        self._base = f"{graph_api_base.rstrip('/')}/{graph_api_version}"
        self._timeout = timeout_seconds

    def _error(self, response: httpx.Response) -> SendResult:
        code = f"http_{response.status_code}"
        message = "Meta rejected the request"
        try:
            error = response.json().get("error", {})
            code = str(error.get("code", code))
            message = str(error.get("message", message))
        except (ValueError, AttributeError):
            pass
        logger.warning(
            "meta_channel_api_error",
            extra={"provider_code": code, "channel_type": self._channel_type.value},
        )
        return SendResult(success=False, error_code=code, error_message=message[:500])

    def send_text(
        self, credentials: dict[str, Any], recipient_external_id: str, text: str
    ) -> SendResult:
        token = str(credentials.get("access_token", ""))
        account_id = str(credentials.get("account_id", ""))
        if not token or not account_id:
            return SendResult(
                success=False,
                error_code="not_configured",
                error_message="Meta channel credentials are incomplete",
            )
        if self._channel_type in {
            ChannelType.FACEBOOK_COMMENTS,
            ChannelType.INSTAGRAM_COMMENTS,
        }:
            url = f"{self._base}/{recipient_external_id}/comments"
            payload: dict[str, Any] = {"message": text, "access_token": token}
        else:
            url = f"{self._base}/{account_id}/messages"
            payload = {
                "recipient": {"id": recipient_external_id},
                "message": {"text": text},
                "access_token": token,
            }
        try:
            response = httpx.post(url, json=payload, timeout=self._timeout)
            if response.is_error:
                return self._error(response)
            body = response.json()
            external_id = str(
                body.get("message_id") or body.get("id") or body.get("recipient_id") or ""
            )
            return SendResult(success=True, external_id=external_id or None)
        except httpx.HTTPError:
            logger.warning(
                "meta_channel_transport_error",
                extra={"channel_type": self._channel_type.value},
            )
            return SendResult(
                success=False,
                error_code="transport_error",
                error_message="Meta could not be reached",
            )

    def send_template(
        self,
        credentials: dict[str, Any],
        recipient_external_id: str,
        name: str,
        language: str,
        parameters: list[str],
    ) -> SendResult:
        del name, language
        return self.send_text(credentials, recipient_external_id, " ".join(parameters))

    def send_media(
        self,
        credentials: dict[str, Any],
        recipient_external_id: str,
        media_type: str,
        url: str,
        caption: str,
        filename: str | None,
    ) -> SendResult:
        del credentials, recipient_external_id, media_type, url, caption, filename
        return SendResult(
            success=False,
            error_code="unsupported_media",
            error_message="Media sending is not enabled for this Meta channel",
        )

    def check_connection(self, credentials: dict[str, Any]) -> tuple[bool, str | None]:
        token = str(credentials.get("access_token", ""))
        account_id = str(credentials.get("account_id", ""))
        if not token or not account_id:
            return False, "not_configured"
        try:
            response = httpx.get(
                f"{self._base}/{account_id}",
                params={"fields": "id,name,username", "access_token": token},
                timeout=self._timeout,
            )
            if response.is_error:
                result = self._error(response)
                return False, result.error_code
            return True, None
        except httpx.HTTPError:
            return False, "transport_error"
