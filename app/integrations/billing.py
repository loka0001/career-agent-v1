"""Subscription billing providers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Protocol
from urllib.parse import quote

from app.domain.errors import IntegrationNotConfiguredError
from app.domain.models import CheckoutLink
from app.integrations.stripe_api import StripeApi, StripeEvent


class BillingProvider(Protocol):
    name: str

    def change_plan(self, organization_id: str, plan_key: str) -> tuple[str, str]: ...

    def create_checkout(
        self,
        organization_id: str,
        plan_key: str,
        customer_id: str | None,
        customer_email: str | None,
        public_base_url: str,
    ) -> CheckoutLink: ...

    def create_portal(self, customer_id: str, public_base_url: str) -> CheckoutLink: ...

    def verify_event(self, body: bytes, signature_header: str) -> StripeEvent: ...

    def retrieve_subscription(self, subscription_id: str) -> dict[str, object]: ...

    def plan_for_price(self, price_id: str) -> str | None: ...


class DemoBillingProvider:
    name = "demo"

    def change_plan(self, organization_id: str, plan_key: str) -> tuple[str, str]:
        customer_id = f"demo-customer-{organization_id}"
        subscription_id = f"demo-sub-{plan_key}-{uuid.uuid4().hex[:8]}"
        return customer_id, subscription_id

    def create_checkout(
        self,
        organization_id: str,
        plan_key: str,
        customer_id: str | None,
        customer_email: str | None,
        public_base_url: str,
    ) -> CheckoutLink:
        del organization_id, plan_key, customer_id, customer_email, public_base_url
        raise IntegrationNotConfiguredError("Demo billing does not use Checkout")

    def create_portal(self, customer_id: str, public_base_url: str) -> CheckoutLink:
        del customer_id, public_base_url
        raise IntegrationNotConfiguredError("Demo billing does not use a customer portal")

    def verify_event(self, body: bytes, signature_header: str) -> StripeEvent:
        del body, signature_header
        raise IntegrationNotConfiguredError("Stripe billing is not configured")

    def retrieve_subscription(self, subscription_id: str) -> dict[str, object]:
        del subscription_id
        raise IntegrationNotConfiguredError("Stripe billing is not configured")

    def plan_for_price(self, price_id: str) -> str | None:
        del price_id
        return None


class StripeBillingProvider:
    name = "stripe"

    def __init__(
        self,
        api: StripeApi,
        prices: dict[str, str],
    ) -> None:
        self.api = api
        self.prices = prices

    def change_plan(self, organization_id: str, plan_key: str) -> tuple[str, str]:
        del organization_id, plan_key
        raise IntegrationNotConfiguredError("Stripe plans are activated only by webhooks")

    def create_checkout(
        self,
        organization_id: str,
        plan_key: str,
        customer_id: str | None,
        customer_email: str | None,
        public_base_url: str,
    ) -> CheckoutLink:
        price_id = self.prices.get(plan_key, "")
        if not price_id:
            raise IntegrationNotConfiguredError("Stripe price is missing for this plan")
        base = public_base_url.rstrip("/")
        data = [
            ("mode", "subscription"),
            ("line_items[0][price]", price_id),
            ("line_items[0][quantity]", "1"),
            ("client_reference_id", organization_id),
            ("metadata[organization_id]", organization_id),
            ("metadata[plan_key]", plan_key),
            ("subscription_data[metadata][organization_id]", organization_id),
            ("subscription_data[metadata][plan_key]", plan_key),
            ("allow_promotion_codes", "true"),
            ("success_url", f"{base}/app/billing?checkout=success"),
            ("cancel_url", f"{base}/app/billing?checkout=cancelled"),
        ]
        if customer_id:
            data.append(("customer", customer_id))
        elif customer_email:
            data.append(("customer_email", customer_email))
        payload = self.api.post(
            "/checkout/sessions",
            data,
            idempotency_key=f"billing:{organization_id}:{plan_key}",
        )
        url = payload.get("url")
        if not isinstance(url, str) or not url.startswith("https://"):
            raise IntegrationNotConfiguredError("Stripe did not return a Checkout URL")
        expires_at = _timestamp(payload.get("expires_at")) or datetime.now(UTC) + timedelta(hours=1)
        return CheckoutLink(provider=self.name, url=url, expires_at=expires_at)

    def create_portal(self, customer_id: str, public_base_url: str) -> CheckoutLink:
        payload = self.api.post(
            "/billing_portal/sessions",
            [
                ("customer", customer_id),
                ("return_url", f"{public_base_url.rstrip('/')}/app/billing"),
            ],
        )
        url = payload.get("url")
        if not isinstance(url, str) or not url.startswith("https://"):
            raise IntegrationNotConfiguredError("Stripe did not return a portal URL")
        return CheckoutLink(
            provider=self.name,
            url=url,
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )

    def verify_event(self, body: bytes, signature_header: str) -> StripeEvent:
        return self.api.verify_event(body, signature_header)

    def retrieve_subscription(self, subscription_id: str) -> dict[str, object]:
        return self.api.get(f"/subscriptions/{quote(subscription_id, safe='')}")

    def plan_for_price(self, price_id: str) -> str | None:
        return next((key for key, value in self.prices.items() if value == price_id), None)


class DisabledBillingProvider(DemoBillingProvider):
    name = "not_configured"

    def change_plan(self, organization_id: str, plan_key: str) -> tuple[str, str]:
        del organization_id, plan_key
        raise IntegrationNotConfiguredError("Subscription billing is not configured")


def _timestamp(value: object) -> datetime | None:
    if not isinstance(value, int):
        return None
    return datetime.fromtimestamp(value, tz=UTC)
