"""Order payment providers with signed demo, COD, and Stripe Checkout."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from app.domain.errors import AuthenticationError, IntegrationNotConfiguredError
from app.domain.models import CheckoutLink
from app.integrations.stripe_api import StripeApi, StripeEvent


@dataclass(frozen=True)
class CreatedPaymentCheckout:
    link: CheckoutLink
    checkout_session_id: str | None = None


class PaymentProvider(Protocol):
    name: str

    def create_checkout(
        self,
        order_id: int,
        store_id: str,
        amount_minor: int,
        currency: str,
        description: str,
        checkout_attempt: str,
        public_base_url: str,
        secret_key: str,
    ) -> CreatedPaymentCheckout: ...

    def verify_checkout(self, order_id: int, token: str, secret_key: str) -> str: ...

    def verify_event(self, body: bytes, signature_header: str) -> StripeEvent: ...


class DemoPaymentProvider:
    name = "demo"

    def _encode(self, payload: dict[str, object], secret_key: str) -> str:
        raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        encoded = base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
        signature = hmac.new(secret_key.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        return f"{encoded}.{signature}"

    def _decode(self, token: str, secret_key: str) -> dict[str, object]:
        try:
            encoded, supplied = token.split(".", 1)
            expected = hmac.new(secret_key.encode(), encoded.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, supplied):
                raise AuthenticationError("Invalid checkout token")
            raw = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
            payload = json.loads(raw)
            if int(payload["exp"]) < int(time.time()):
                raise AuthenticationError("Checkout token expired")
            return dict(payload)
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise AuthenticationError("Invalid checkout token") from exc

    def create_checkout(
        self,
        order_id: int,
        store_id: str,
        amount_minor: int,
        currency: str,
        description: str,
        checkout_attempt: str,
        public_base_url: str,
        secret_key: str,
    ) -> CreatedPaymentCheckout:
        del amount_minor, currency, description, checkout_attempt
        expires_at = datetime.now(UTC) + timedelta(hours=1)
        token = self._encode(
            {
                "order_id": order_id,
                "store_id": store_id,
                "exp": int(expires_at.timestamp()),
            },
            secret_key,
        )
        return CreatedPaymentCheckout(
            link=CheckoutLink(
                provider=self.name,
                url=f"{public_base_url.rstrip('/')}/checkout/demo/{order_id}?token={token}",
                expires_at=expires_at,
            )
        )

    def verify_checkout(self, order_id: int, token: str, secret_key: str) -> str:
        payload = self._decode(token, secret_key)
        token_order_id = payload.get("order_id")
        if not isinstance(token_order_id, int) or token_order_id != order_id:
            raise AuthenticationError("Checkout token does not match order")
        return str(payload.get("store_id", ""))

    def verify_event(self, body: bytes, signature_header: str) -> StripeEvent:
        del body, signature_header
        raise IntegrationNotConfiguredError("Stripe payments are not configured")


class CodPaymentProvider(DemoPaymentProvider):
    name = "cod"

    def create_checkout(
        self,
        order_id: int,
        store_id: str,
        amount_minor: int,
        currency: str,
        description: str,
        checkout_attempt: str,
        public_base_url: str,
        secret_key: str,
    ) -> CreatedPaymentCheckout:
        del store_id, amount_minor, currency, description, checkout_attempt, secret_key
        return CreatedPaymentCheckout(
            link=CheckoutLink(
                provider=self.name,
                url=f"{public_base_url.rstrip('/')}/app/orders?order={order_id}&payment=cod",
                expires_at=datetime.now(UTC) + timedelta(days=7),
            )
        )


class StripePaymentProvider(DemoPaymentProvider):
    name = "stripe"

    def __init__(self, api: StripeApi) -> None:
        self.api = api

    def create_checkout(
        self,
        order_id: int,
        store_id: str,
        amount_minor: int,
        currency: str,
        description: str,
        checkout_attempt: str,
        public_base_url: str,
        secret_key: str,
    ) -> CreatedPaymentCheckout:
        del secret_key
        base = public_base_url.rstrip("/")
        payload = self.api.post(
            "/checkout/sessions",
            [
                ("mode", "payment"),
                ("client_reference_id", str(order_id)),
                ("line_items[0][price_data][currency]", currency.lower()),
                ("line_items[0][price_data][unit_amount]", str(amount_minor)),
                ("line_items[0][price_data][product_data][name]", description),
                ("line_items[0][quantity]", "1"),
                ("metadata[order_id]", str(order_id)),
                ("metadata[store_id]", store_id),
                ("payment_intent_data[metadata][order_id]", str(order_id)),
                ("payment_intent_data[metadata][store_id]", store_id),
                ("success_url", f"{base}/app/orders?checkout=success&order={order_id}"),
                ("cancel_url", f"{base}/app/orders?checkout=cancelled&order={order_id}"),
            ],
            idempotency_key=(
                f"order:{store_id}:{order_id}:{checkout_attempt}:{amount_minor}:{currency.lower()}"
            ),
        )
        session_id = payload.get("id")
        url = payload.get("url")
        if not isinstance(session_id, str) or not isinstance(url, str):
            raise IntegrationNotConfiguredError("Stripe did not return a Checkout Session")
        expires_at = (
            datetime.fromtimestamp(payload["expires_at"], tz=UTC)
            if isinstance(payload.get("expires_at"), int)
            else datetime.now(UTC) + timedelta(hours=1)
        )
        return CreatedPaymentCheckout(
            link=CheckoutLink(provider=self.name, url=url, expires_at=expires_at),
            checkout_session_id=session_id,
        )

    def verify_event(self, body: bytes, signature_header: str) -> StripeEvent:
        return self.api.verify_event(body, signature_header)


class DisabledPaymentProvider(DemoPaymentProvider):
    name = "not_configured"

    def create_checkout(
        self,
        order_id: int,
        store_id: str,
        amount_minor: int,
        currency: str,
        description: str,
        checkout_attempt: str,
        public_base_url: str,
        secret_key: str,
    ) -> CreatedPaymentCheckout:
        del (
            order_id,
            store_id,
            amount_minor,
            currency,
            description,
            checkout_attempt,
            public_base_url,
            secret_key,
        )
        raise IntegrationNotConfiguredError("Customer checkout is not configured")

    def verify_checkout(self, order_id: int, token: str, secret_key: str) -> str:
        del order_id, token, secret_key
        raise IntegrationNotConfiguredError("Customer checkout is not configured")
