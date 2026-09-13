"""Small Stripe API client with strict webhook verification."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.domain.errors import AuthenticationError, ExternalProviderError


@dataclass(frozen=True)
class StripeEvent:
    event_id: str
    event_type: str
    livemode: bool
    account_id: str | None
    created: int
    data: dict[str, Any]


class StripeApi:
    def __init__(
        self,
        secret_key: str,
        webhook_secret: str,
        *,
        timeout_seconds: float = 30,
        client: httpx.Client | None = None,
    ) -> None:
        self.secret_key = secret_key
        self.webhook_secret = webhook_secret
        self._client = client or httpx.Client(
            base_url="https://api.stripe.com/v1",
            auth=(secret_key, ""),
            timeout=timeout_seconds,
        )

    def post(
        self,
        path: str,
        data: list[tuple[str, str]],
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else {}
        try:
            response = self._client.post(path, data=dict(data), headers=headers)
        except httpx.HTTPError as exc:
            raise ExternalProviderError("Stripe request failed") from exc
        if response.is_error:
            request_id = response.headers.get("request-id", "")
            try:
                error = response.json().get("error", {})
            except (ValueError, AttributeError):
                error = {}
            raise ExternalProviderError(
                "Stripe rejected the request",
                details={
                    "provider": "stripe",
                    "code": str(error.get("code") or error.get("type") or "request_failed"),
                    "request_id": request_id,
                },
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise ExternalProviderError("Stripe returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise ExternalProviderError("Stripe returned an invalid response")
        return dict(payload)

    def get(self, path: str) -> dict[str, Any]:
        try:
            response = self._client.get(path)
        except httpx.HTTPError as exc:
            raise ExternalProviderError("Stripe request failed") from exc
        if response.is_error:
            raise ExternalProviderError(
                "Stripe rejected the request",
                details={
                    "provider": "stripe",
                    "request_id": response.headers.get("request-id", ""),
                },
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise ExternalProviderError("Stripe returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise ExternalProviderError("Stripe returned an invalid response")
        return dict(payload)

    def verify_event(
        self,
        body: bytes,
        signature_header: str,
        *,
        tolerance_seconds: int = 300,
        now: int | None = None,
    ) -> StripeEvent:
        if not self.webhook_secret or not signature_header:
            raise AuthenticationError("Missing Stripe webhook signature")
        timestamp: int | None = None
        signatures: list[str] = []
        for item in signature_header.split(","):
            key, separator, value = item.strip().partition("=")
            if not separator:
                continue
            if key == "t":
                try:
                    timestamp = int(value)
                except ValueError:
                    timestamp = None
            elif key == "v1":
                signatures.append(value)
        current_time = int(time.time()) if now is None else now
        if timestamp is None or abs(current_time - timestamp) > tolerance_seconds:
            raise AuthenticationError("Expired Stripe webhook signature")
        signed = str(timestamp).encode() + b"." + body
        expected = hmac.new(
            self.webhook_secret.encode(),
            signed,
            hashlib.sha256,
        ).hexdigest()
        if not signatures or not any(
            hmac.compare_digest(expected, supplied) for supplied in signatures
        ):
            raise AuthenticationError("Invalid Stripe webhook signature")
        try:
            raw = json.loads(body)
        except json.JSONDecodeError as exc:
            raise AuthenticationError("Invalid Stripe webhook payload") from exc
        if not isinstance(raw, dict) or not isinstance(raw.get("data"), dict):
            raise AuthenticationError("Invalid Stripe webhook event")
        data_object = raw["data"].get("object")
        if not isinstance(data_object, dict):
            raise AuthenticationError("Invalid Stripe webhook object")
        event_id = raw.get("id")
        event_type = raw.get("type")
        created = raw.get("created")
        if not isinstance(event_id, str) or not isinstance(event_type, str):
            raise AuthenticationError("Invalid Stripe webhook identity")
        return StripeEvent(
            event_id=event_id,
            event_type=event_type,
            livemode=bool(raw.get("livemode", False)),
            account_id=str(raw["account"]) if raw.get("account") else None,
            created=int(created) if isinstance(created, int) else timestamp,
            data=dict(data_object),
        )
