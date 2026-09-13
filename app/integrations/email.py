"""Transactional email adapters used by account and invitation workflows."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Protocol

import httpx

from app.config import Settings
from app.domain.errors import ExternalProviderError, IntegrationNotConfiguredError


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    text: str
    action_url: str
    idempotency_key: str


class EmailSender(Protocol):
    @property
    def available(self) -> bool: ...

    def send(self, message: EmailMessage) -> None: ...


class DisabledEmailSender:
    @property
    def available(self) -> bool:
        return False

    def send(self, message: EmailMessage) -> None:
        del message
        raise IntegrationNotConfiguredError("Transactional email is not configured")


class RecordingEmailSender:
    """In-memory delivery sink limited to tests and explicit demo mode."""

    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []

    @property
    def available(self) -> bool:
        return True

    def send(self, message: EmailMessage) -> None:
        self.messages.append(message)


class ResendEmailSender:
    def __init__(self, api_key: str, from_address: str, timeout_seconds: float = 15.0):
        self._api_key = api_key
        self._from_address = from_address
        self._timeout_seconds = timeout_seconds

    @property
    def available(self) -> bool:
        return bool(self._api_key and self._from_address)

    def send(self, message: EmailMessage) -> None:
        safe_text = escape(message.text).replace("\n", "<br>")
        safe_url = escape(message.action_url, quote=True)
        try:
            response = httpx.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                    "Idempotency-Key": message.idempotency_key,
                },
                json={
                    "from": self._from_address,
                    "to": [message.to],
                    "subject": message.subject,
                    "text": f"{message.text}\n\n{message.action_url}",
                    "html": (
                        '<div dir="rtl" style="font-family:Arial,sans-serif;line-height:1.8">'
                        f"<p>{safe_text}</p>"
                        f'<p><a href="{safe_url}">متابعة الإجراء بأمان</a></p>'
                        "<p>ينتهي هذا الرابط تلقائيًا ولا يمكن استخدامه أكثر من مرة.</p>"
                        "</div>"
                    ),
                },
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ExternalProviderError("Transactional email delivery failed") from exc


def build_email_sender(settings: Settings) -> EmailSender:
    if settings.email_provider == "resend":
        return ResendEmailSender(
            settings.resend_api_key.get_secret_value(),
            settings.email_from,
        )
    if settings.app_env == "test" or settings.demo_mode:
        return RecordingEmailSender()
    return DisabledEmailSender()
