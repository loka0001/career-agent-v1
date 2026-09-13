"""Channel adapters: one protocol, demo implementation, registry by channel type.

Live adapters (WhatsApp Cloud API, Meta DMs) are added in their own modules and
registered here; every adapter must be safe to call from a background job.
"""

from __future__ import annotations

import uuid
from typing import Any, Protocol

from app.domain.enums import ChannelMode, ChannelType
from app.domain.models import SendResult


class ChannelAdapter(Protocol):
    """Sends one text message to an external recipient."""

    def send_text(
        self, credentials: dict[str, Any], recipient_external_id: str, text: str
    ) -> SendResult: ...

    def send_template(
        self,
        credentials: dict[str, Any],
        recipient_external_id: str,
        name: str,
        language: str,
        parameters: list[str],
    ) -> SendResult: ...

    def send_media(
        self,
        credentials: dict[str, Any],
        recipient_external_id: str,
        media_type: str,
        url: str,
        caption: str,
        filename: str | None,
    ) -> SendResult: ...

    def check_connection(self, credentials: dict[str, Any]) -> tuple[bool, str | None]: ...


class DemoChannelAdapter:
    """Always succeeds locally; never performs network calls."""

    def send_text(
        self, credentials: dict[str, Any], recipient_external_id: str, text: str
    ) -> SendResult:
        del credentials, recipient_external_id, text
        return SendResult(success=True, external_id=f"demo-{uuid.uuid4().hex[:12]}")

    def send_template(
        self,
        credentials: dict[str, Any],
        recipient_external_id: str,
        name: str,
        language: str,
        parameters: list[str],
    ) -> SendResult:
        del credentials, recipient_external_id, name, language, parameters
        return SendResult(success=True, external_id=f"demo-template-{uuid.uuid4().hex[:12]}")

    def check_connection(self, credentials: dict[str, Any]) -> tuple[bool, str | None]:
        del credentials
        return True, None

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
        return SendResult(success=True, external_id=f"demo-media-{uuid.uuid4().hex[:12]}")


_LIVE_ADAPTERS: dict[ChannelType, ChannelAdapter] = {}
_DEMO_ADAPTER = DemoChannelAdapter()


def register_live_adapter(channel_type: ChannelType, adapter: ChannelAdapter) -> None:
    _LIVE_ADAPTERS[channel_type] = adapter


def resolve_adapter(channel_type: ChannelType, mode: ChannelMode) -> ChannelAdapter:
    if mode == ChannelMode.LIVE:
        adapter = _LIVE_ADAPTERS.get(channel_type)
        if adapter is not None:
            return adapter
        raise LookupError(f"No live adapter registered for channel '{channel_type.value}'")
    return _DEMO_ADAPTER
