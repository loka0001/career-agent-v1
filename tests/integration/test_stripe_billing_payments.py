from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import select

from app.db.models import (
    ConversationModel,
    OrderModel,
    OrganizationModel,
    PaymentTransactionModel,
    StoreModel,
    SubscriptionModel,
)
from app.domain.errors import AuthenticationError, QuotaExceededError
from app.integrations.billing import StripeBillingProvider
from app.integrations.payments import StripePaymentProvider
from app.integrations.stripe_api import StripeApi
from app.services.billing import check_and_increment, handle_billing_webhook
from app.services.orders import create_order_checkout, handle_payment_webhook


def _signed_event(
    secret: str,
    event_type: str,
    data: dict[str, object],
    *,
    event_id: str | None = None,
    created: int | None = None,
) -> tuple[bytes, str]:
    timestamp = created or int(time.time())
    body = json.dumps(
        {
            "id": event_id or f"evt_{uuid.uuid4().hex}",
            "type": event_type,
            "created": timestamp,
            "livemode": False,
            "data": {"object": data},
        },
        separators=(",", ":"),
    ).encode()
    signature = hmac.new(
        secret.encode(),
        str(timestamp).encode() + b"." + body,
        hashlib.sha256,
    ).hexdigest()
    return body, f"t={timestamp},v1={signature}"


def _mock_client(handler) -> httpx.Client:
    return httpx.Client(
        base_url="https://api.stripe.com/v1",
        transport=httpx.MockTransport(handler),
    )


def test_stripe_signature_rejects_tampering_and_expiry() -> None:
    secret = "whsec_test_signature"
    body, signature = _signed_event(
        secret,
        "checkout.session.completed",
        {"id": "cs_test", "metadata": {}},
    )
    api = StripeApi("sk_test", secret, client=_mock_client(lambda _: httpx.Response(200)))
    assert api.verify_event(body, signature).event_type == "checkout.session.completed"
    with pytest.raises(AuthenticationError):
        api.verify_event(body + b" ", signature)
    old_body, old_signature = _signed_event(
        secret,
        "checkout.session.completed",
        {"id": "cs_old", "metadata": {}},
        created=int(time.time()) - 301,
    )
    with pytest.raises(AuthenticationError):
        api.verify_event(old_body, old_signature)


def test_stripe_billing_webhook_is_authoritative_and_idempotent(context) -> None:
    secret = "whsec_billing_test"
    with context.session_factory() as session:
        store = session.get(StoreModel, "demo-store")
        assert store is not None and store.organization_id is not None
        organization_id = store.organization_id

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/subscriptions/sub_test"
        return httpx.Response(
            200,
            json={
                "id": "sub_test",
                "customer": "cus_test",
                "status": "active",
                "metadata": {
                    "organization_id": organization_id,
                    "plan_key": "starter",
                },
                "current_period_start": int(time.time()) - 60,
                "current_period_end": int(time.time()) + 2_592_000,
                "cancel_at_period_end": False,
            },
        )

    provider = StripeBillingProvider(
        StripeApi(
            "sk_test",
            secret,
            client=_mock_client(handler),
        ),
        {
            "starter": "price_starter",
            "growth": "price_growth",
            "pro": "price_pro",
        },
    )
    body, signature = _signed_event(
        secret,
        "checkout.session.completed",
        {
            "id": "cs_subscription",
            "mode": "subscription",
            "subscription": "sub_test",
            "metadata": {
                "organization_id": organization_id,
                "plan_key": "starter",
            },
        },
        event_id=f"evt_billing_{uuid.uuid4().hex}",
    )
    with context.session_factory.begin() as session:
        assert handle_billing_webhook(session, provider, body, signature) is True
        assert handle_billing_webhook(session, provider, body, signature) is False
    current = context.client.get(
        "/api/v1/billing/subscription",
        headers=context.login(),
    )
    assert current.status_code == 200
    assert current.json()["provider"] == "stripe"
    assert current.json()["plan"]["key"] == "starter"

    failed_body, failed_signature = _signed_event(
        secret,
        "invoice.payment_failed",
        {
            "id": "in_failed",
            "subscription": "sub_test",
            "customer": "cus_test",
        },
        created=int(time.time()) + 1,
    )
    with context.session_factory.begin() as session:
        assert handle_billing_webhook(
            session,
            provider,
            failed_body,
            failed_signature,
        )
        with pytest.raises(QuotaExceededError):
            check_and_increment(session, "demo-store", "ai_operations")
        subscription = session.scalar(
            select(SubscriptionModel).where(SubscriptionModel.organization_id == organization_id)
        )
        organization = session.get(OrganizationModel, organization_id)
        assert subscription is not None and organization is not None
        subscription.provider = "demo"
        subscription.status = "active"
        subscription.plan_key = "growth"
        subscription.last_provider_event_at = None
        organization.plan = "growth"


def test_stripe_order_checkout_payment_and_refund_are_idempotent(authenticated) -> None:
    context, headers = authenticated
    with context.session_factory() as session:
        conversation_id = session.scalar(
            select(ConversationModel.id)
            .where(ConversationModel.store_id == "demo-store")
            .order_by(ConversationModel.id)
        )
    assert conversation_id is not None
    created_order = context.client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "conversation_id": conversation_id,
            "items": [{"product_id": "A103", "quantity": 1}],
            "discount": "0",
            "shipping": {"city": "Cairo"},
        },
    )
    assert created_order.status_code == 201, created_order.text
    order_id = created_order.json()["id"]
    secret = "whsec_payment_test"
    checkout_id = f"cs_{uuid.uuid4().hex}"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/checkout/sessions"
        return httpx.Response(
            200,
            json={
                "id": checkout_id,
                "url": f"https://checkout.stripe.com/c/pay/{checkout_id}",
                "expires_at": int(time.time()) + 3600,
            },
        )

    provider = StripePaymentProvider(
        StripeApi(
            "sk_test",
            secret,
            client=_mock_client(handler),
        )
    )
    with context.session_factory.begin() as session:
        store = session.get(StoreModel, "demo-store")
        order = session.get(OrderModel, order_id)
        assert store is not None
        assert order is not None and order.created_by_user_id is not None
        link = create_order_checkout(
            session,
            store.id,
            order_id,
            order.created_by_user_id,
            "https://commerce.example",
            "app-secret",
            provider,
        )
        assert link.provider == "stripe"
        transaction = session.scalar(
            select(PaymentTransactionModel).where(
                PaymentTransactionModel.order_id == order_id,
                PaymentTransactionModel.checkout_session_id == checkout_id,
            )
        )
        assert transaction is not None
        amount_minor = int(transaction.amount_numeric * 100)
        currency = transaction.currency.lower()

    paid_body, paid_signature = _signed_event(
        secret,
        "checkout.session.completed",
        {
            "id": checkout_id,
            "payment_status": "paid",
            "payment_intent": "pi_test_order",
            "amount_total": amount_minor,
            "currency": currency,
            "metadata": {
                "order_id": str(order_id),
                "store_id": "demo-store",
            },
        },
    )
    with context.session_factory.begin() as session:
        assert handle_payment_webhook(session, provider, paid_body, paid_signature) is True
        assert handle_payment_webhook(session, provider, paid_body, paid_signature) is False
        order = session.get(OrderModel, order_id)
        assert order is not None and order.status == "paid"

    refund_body, refund_signature = _signed_event(
        secret,
        "charge.refunded",
        {
            "id": "ch_refunded",
            "payment_intent": "pi_test_order",
            "amount_refunded": amount_minor,
        },
        created=int(datetime.now(UTC).timestamp()) + 1,
    )
    with context.session_factory.begin() as session:
        assert handle_payment_webhook(session, provider, refund_body, refund_signature)
        order = session.get(OrderModel, order_id)
        transaction = session.scalar(
            select(PaymentTransactionModel).where(PaymentTransactionModel.order_id == order_id)
        )
        assert order is not None and order.status == "refunded"
        assert transaction is not None and transaction.status == "refunded"
