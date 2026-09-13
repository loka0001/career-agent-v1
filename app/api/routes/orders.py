"""Orders created from inbox conversations and a signed demo checkout."""

from __future__ import annotations

import html

from fastapi import APIRouter, Form, Header, Request
from fastapi.responses import HTMLResponse

from app.api.dependencies import AgentUser, ContainerDependency, CurrentUser, DatabaseDependency
from app.api.request_body import read_bounded_body
from app.domain.models import (
    CheckoutLink,
    DraftOrderInput,
    OrderOut,
    OrderTransitionInput,
)
from app.services.orders import (
    confirm_demo_checkout,
    create_draft_order,
    create_order_checkout,
    handle_payment_webhook,
    list_orders,
    notify_order_status,
    order_out,
    schedule_post_delivery,
    transition_order,
)

router = APIRouter(prefix="/orders", tags=["orders"])
checkout_router = APIRouter(prefix="/checkout/demo", tags=["demo-checkout"])
webhook_router = APIRouter(prefix="/webhooks/stripe", tags=["stripe-webhooks"])


@router.get("", response_model=list[OrderOut])
def orders(user: CurrentUser, db: DatabaseDependency) -> list[OrderOut]:
    return list_orders(db, user.store_id)


@router.post("", response_model=OrderOut, status_code=201)
def add_order(payload: DraftOrderInput, user: AgentUser, db: DatabaseDependency) -> OrderOut:
    return create_draft_order(db, user.store_id, user.user_id, payload)


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, user: CurrentUser, db: DatabaseDependency) -> OrderOut:
    return order_out(db, user.store_id, order_id)


@router.post("/{order_id}/transition", response_model=OrderOut)
def change_status(
    order_id: int,
    payload: OrderTransitionInput,
    user: AgentUser,
    db: DatabaseDependency,
) -> OrderOut:
    order = transition_order(
        db,
        user.store_id,
        order_id,
        payload.status,
        actor_user_id=user.user_id,
        reason=payload.reason,
    )
    if payload.notify_customer:
        notify_order_status(db, user.store_id, order_id, payload.status)
    if payload.status.value == "delivered":
        schedule_post_delivery(db, user.store_id, order_id)
    return order


@router.post("/{order_id}/checkout", response_model=CheckoutLink)
def checkout(
    order_id: int,
    user: AgentUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> CheckoutLink:
    return create_order_checkout(
        db,
        user.store_id,
        order_id,
        user.user_id,
        container.settings.public_base_url,
        container.settings.effective_secret_key,
        container.payment_provider,
    )


@webhook_router.post("/payments")
async def stripe_payment_webhook(
    request: Request,
    container: ContainerDependency,
    db: DatabaseDependency,
    stripe_signature: str = Header(default="", alias="Stripe-Signature"),
) -> dict[str, bool]:
    body = await read_bounded_body(request, max_bytes=1024 * 1024, label="Stripe webhook")
    processed = handle_payment_webhook(
        db,
        container.payment_provider,
        body,
        stripe_signature,
    )
    return {"received": True, "processed": processed}


@checkout_router.get("/{order_id}", response_class=HTMLResponse)
def checkout_page(order_id: int, token: str) -> HTMLResponse:
    safe_token = html.escape(token, quote=True)
    return HTMLResponse(
        f"""<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8">
<meta name="viewport" content="width=device-width"><title>Demo Checkout</title>
<style>body{{font-family:system-ui;background:#0b1020;color:#f8fafc;display:grid;
place-items:center;min-height:100vh;margin:0}}main{{max-width:28rem;padding:2rem;
border:1px solid #334155;border-radius:8px;background:#111827}}button{{width:100%;
padding:.9rem;border:0;border-radius:6px;background:#22c55e;color:#052e16;
font-weight:800;cursor:pointer}}</style><main><h1>طلب #{order_id}</h1>
<p>هذه صفحة دفع تجريبية، ولا تخصم أي أموال حقيقية.</p>
<form method="post"><input type="hidden" name="token" value="{safe_token}">
<button type="submit">تأكيد الدفع التجريبي</button></form></main></html>"""
    )


@checkout_router.post("/{order_id}", response_class=HTMLResponse)
def confirm_checkout(
    order_id: int,
    container: ContainerDependency,
    db: DatabaseDependency,
    token: str = Form(),
) -> HTMLResponse:
    order = confirm_demo_checkout(
        db,
        order_id,
        token,
        container.settings.effective_secret_key,
        container.payment_provider,
    )
    return HTMLResponse(
        f"""<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8">
<title>تم الدفع</title><body><h1>تم تأكيد الطلب #{order.id}</h1>
<p>الحالة: {order.status.value}</p></body></html>"""
    )
