"""Authoritative order creation, legal transitions, and demo checkout."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import (
    ConversationModel,
    OrderItemModel,
    OrderModel,
    OrderTransitionModel,
    PaymentTransactionModel,
    ProductModel,
    ProductVariantModel,
    StripeEventModel,
)
from app.domain.enums import OrderStatus, ProductStatus
from app.domain.errors import ConflictError, NotFoundError
from app.domain.models import (
    CheckoutLink,
    DraftOrderInput,
    OrderItemOut,
    OrderOut,
    OrderTimelineEntry,
)
from app.integrations.payments import PaymentProvider
from app.integrations.stripe_api import StripeEvent
from app.services.conversations import queue_outbound_message
from app.services.inventory import adjust_inventory
from app.services.job_queue import enqueue_job, job_handler

LEGAL_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.DRAFT: {OrderStatus.PENDING, OrderStatus.CANCELLED},
    OrderStatus.PENDING: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.PAID, OrderStatus.CANCELLED},
    OrderStatus.PAID: {OrderStatus.PROCESSING, OrderStatus.REFUNDED},
    OrderStatus.PROCESSING: {OrderStatus.SHIPPED, OrderStatus.REFUNDED},
    OrderStatus.SHIPPED: {OrderStatus.DELIVERED, OrderStatus.REFUNDED},
    OrderStatus.DELIVERED: {OrderStatus.REFUNDED},
    OrderStatus.CANCELLED: set(),
    OrderStatus.REFUNDED: set(),
}


def _order_row(session: Session, store_id: str, order_id: int, *, lock: bool = False) -> OrderModel:
    statement = select(OrderModel).where(
        OrderModel.id == order_id,
        OrderModel.store_id == store_id,
    )
    if lock:
        statement = statement.with_for_update()
    order = session.scalar(statement)
    if order is None:
        raise NotFoundError(details={"entity": "order", "id": order_id})
    return order


def _change_inventory_reservation(session: Session, order: OrderModel, *, reserve: bool) -> None:
    if order.inventory_reserved == reserve:
        return
    items = session.scalars(
        select(OrderItemModel)
        .where(OrderItemModel.order_id == order.id)
        .order_by(OrderItemModel.product_pk)
    ).all()
    for item in items:
        adjust_inventory(
            session,
            store_id=order.store_id,
            product_id=item.product_id,
            variant_id=item.variant_id,
            delta=-item.quantity if reserve else item.quantity,
            reason="order_reservation" if reserve else "order_release",
            idempotency_key=(
                f"order:{order.id}:reserve:{item.id}"
                if reserve
                else f"order:{order.id}:release:{item.id}"
            ),
            reference_type="order",
            reference_id=str(order.id),
        )
    order.inventory_reserved = reserve
    session.flush()


def order_out(session: Session, store_id: str, order_id: int) -> OrderOut:
    order = _order_row(session, store_id, order_id)
    payment = session.scalar(
        select(PaymentTransactionModel)
        .where(
            PaymentTransactionModel.order_id == order.id,
            PaymentTransactionModel.store_id == store_id,
        )
        .order_by(PaymentTransactionModel.id.desc())
    )
    items = session.scalars(
        select(OrderItemModel)
        .where(OrderItemModel.order_id == order.id)
        .order_by(OrderItemModel.id)
    ).all()
    transitions = session.scalars(
        select(OrderTransitionModel)
        .where(OrderTransitionModel.order_id == order.id)
        .order_by(OrderTransitionModel.created_at, OrderTransitionModel.id)
    ).all()
    return OrderOut(
        id=order.id,
        customer_id=order.customer_id,
        conversation_id=order.conversation_id,
        status=OrderStatus(order.status),
        currency=order.currency,
        subtotal=order.subtotal_numeric,
        discount=order.discount_numeric,
        shipping_total=order.shipping_total_numeric,
        tax_total=order.tax_total_numeric,
        total=order.total_numeric,
        shipping={str(key): str(value) for key, value in order.shipping_json.items()},
        notes=order.notes,
        payment_provider=payment.provider if payment else None,
        payment_status=payment.status if payment else order.payment_status,
        fulfillment_status=order.fulfillment_status,
        provider_references=dict(order.provider_references_json),
        idempotency_key=order.idempotency_key,
        refunded_amount=payment.refunded_amount_numeric if payment else Decimal("0"),
        items=[
            OrderItemOut(
                product_id=item.product_id,
                variant_id=item.variant_id,
                sku=item.sku,
                options=dict(item.options_json),
                product_name=item.product_name,
                unit_price=item.unit_price_numeric,
                quantity=item.quantity,
                line_total=item.line_total_numeric,
            )
            for item in items
        ],
        timeline=[
            OrderTimelineEntry(
                from_status=OrderStatus(row.from_status) if row.from_status else None,
                to_status=OrderStatus(row.to_status),
                actor_user_id=row.actor_user_id,
                reason=row.reason,
                created_at=row.created_at,
            )
            for row in transitions
        ],
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


def list_orders(session: Session, store_id: str) -> list[OrderOut]:
    ids = session.scalars(
        select(OrderModel.id)
        .where(OrderModel.store_id == store_id)
        .order_by(OrderModel.updated_at.desc())
        .limit(200)
    ).all()
    return [order_out(session, store_id, order_id) for order_id in ids]


def create_draft_order(
    session: Session,
    store_id: str,
    actor_user_id: str | None,
    payload: DraftOrderInput,
) -> OrderOut:
    if payload.idempotency_key:
        existing_order = session.scalar(
            select(OrderModel).where(
                OrderModel.store_id == store_id,
                OrderModel.idempotency_key == payload.idempotency_key,
            )
        )
        if existing_order is not None:
            return order_out(session, store_id, existing_order.id)
    conversation = session.scalar(
        select(ConversationModel).where(
            ConversationModel.id == payload.conversation_id,
            ConversationModel.store_id == store_id,
        )
    )
    if conversation is None:
        raise NotFoundError(details={"entity": "conversation", "id": payload.conversation_id})
    requested: dict[tuple[str, str | None], int] = {}
    for item in payload.items:
        key = (item.product_id, item.variant_id)
        requested[key] = requested.get(key, 0) + item.quantity
    products = session.scalars(
        select(ProductModel).where(
            ProductModel.store_id == store_id,
            ProductModel.product_id.in_({key[0] for key in requested}),
        )
    ).all()
    by_id = {product.product_id: product for product in products}
    missing = sorted({key[0] for key in requested} - set(by_id))
    if missing:
        raise NotFoundError(details={"entity": "product", "ids": missing})
    variants = session.scalars(
        select(ProductVariantModel).where(
            ProductVariantModel.store_id == store_id,
            ProductVariantModel.product_pk.in_([product.id for product in products]),
        )
    ).all()
    by_variant = {(row.product_pk, row.variant_id): row for row in variants}
    subtotal = Decimal("0")
    resolved: dict[tuple[str, str | None], ProductVariantModel | None] = {}
    for (product_id, variant_id), quantity in requested.items():
        product = by_id[product_id]
        matching = [
            row for row in variants if row.product_pk == product.id and row.status == "active"
        ]
        variant = (
            by_variant.get((product.id, variant_id))
            if variant_id is not None
            else matching[0]
            if len(matching) == 1
            else None
        )
        if variant_id is not None and variant is None:
            raise NotFoundError(details={"entity": "variant", "variant_id": variant_id})
        if variant_id is None and len(matching) > 1:
            raise ConflictError(
                "A variant is required for products with multiple variants",
                details={"product_id": product_id},
            )
        target = variant if variant is not None else product
        if (
            product.status != ProductStatus.ACTIVE.value
            or getattr(target, "status", "active") != "active"
            or (target.stock < quantity and target.stock_policy != "continue")
        ):
            raise ConflictError(
                "Product is unavailable in the requested quantity",
                details={"product_id": product_id, "available": target.stock},
            )
        subtotal += target.price_numeric * quantity
        resolved[(product_id, variant_id)] = variant
    if payload.discount > subtotal:
        raise ConflictError("Order discount cannot exceed subtotal")
    total = subtotal - payload.discount + payload.shipping_total + payload.tax_total
    order = OrderModel(
        store_id=store_id,
        customer_id=conversation.customer_id,
        conversation_id=conversation.id,
        status=OrderStatus.DRAFT.value,
        payment_status="unpaid",
        fulfillment_status="unfulfilled",
        currency=payload.currency.upper(),
        subtotal_numeric=subtotal,
        discount_numeric=payload.discount,
        shipping_total_numeric=payload.shipping_total,
        tax_total_numeric=payload.tax_total,
        total_numeric=total,
        shipping_json=payload.shipping,
        idempotency_key=payload.idempotency_key,
        notes=payload.notes,
        created_by_user_id=actor_user_id,
    )
    session.add(order)
    session.flush()
    for (product_id, variant_id), quantity in requested.items():
        product = by_id[product_id]
        variant = resolved[(product_id, variant_id)]
        unit_price = variant.price_numeric if variant is not None else product.price_numeric
        session.add(
            OrderItemModel(
                order_id=order.id,
                product_pk=product.id,
                variant_pk=variant.id if variant is not None else None,
                product_id=product.product_id,
                variant_id=variant.variant_id if variant is not None else None,
                sku=variant.sku if variant is not None else product.sku,
                options_json=dict(variant.options_json) if variant is not None else {},
                product_name=product.name,
                unit_price_numeric=unit_price,
                quantity=quantity,
                line_total_numeric=unit_price * quantity,
            )
        )
    session.add(
        OrderTransitionModel(
            order_id=order.id,
            from_status=None,
            to_status=OrderStatus.DRAFT.value,
            actor_user_id=actor_user_id,
            reason="created_from_conversation",
        )
    )
    session.flush()
    return order_out(session, store_id, order.id)


def transition_order(
    session: Session,
    store_id: str,
    order_id: int,
    target: OrderStatus,
    *,
    actor_user_id: str | None,
    reason: str = "",
) -> OrderOut:
    order = _order_row(session, store_id, order_id, lock=True)
    current = OrderStatus(order.status)
    payment = session.scalar(
        select(PaymentTransactionModel)
        .where(
            PaymentTransactionModel.order_id == order.id,
            PaymentTransactionModel.store_id == store_id,
        )
        .order_by(PaymentTransactionModel.id.desc())
    )
    if (
        actor_user_id is not None
        and target == OrderStatus.PAID
        and payment is not None
        and payment.provider == "stripe"
        and payment.status != "paid"
    ):
        raise ConflictError("Stripe payments can only be confirmed by a signed webhook")
    if (
        actor_user_id is not None
        and target == OrderStatus.REFUNDED
        and payment is not None
        and payment.provider == "stripe"
    ):
        raise ConflictError("Refund the payment in Stripe; the webhook will update the order")
    if target not in LEGAL_TRANSITIONS[current]:
        raise ConflictError(
            "Illegal order status transition",
            details={"from": current.value, "to": target.value},
        )
    if target == OrderStatus.PENDING:
        _change_inventory_reservation(session, order, reserve=True)
    elif target == OrderStatus.CANCELLED and order.inventory_reserved:
        _change_inventory_reservation(session, order, reserve=False)
    order.status = target.value
    if target == OrderStatus.PAID:
        order.payment_status = "paid"
    elif target == OrderStatus.REFUNDED:
        order.payment_status = "refunded"
    elif target == OrderStatus.CANCELLED and order.payment_status == "unpaid":
        order.payment_status = "cancelled"
    fulfillment_by_status = {
        OrderStatus.PROCESSING: "processing",
        OrderStatus.SHIPPED: "shipped",
        OrderStatus.DELIVERED: "fulfilled",
        OrderStatus.CANCELLED: "cancelled",
    }
    if target in fulfillment_by_status:
        order.fulfillment_status = fulfillment_by_status[target]
    order.updated_at = datetime.now(UTC)
    if payment is not None and payment.provider == "cod":
        if target == OrderStatus.PAID:
            payment.status = "paid"
        elif target == OrderStatus.CANCELLED:
            payment.status = "cancelled"
        elif target == OrderStatus.REFUNDED:
            payment.status = "refunded"
            payment.refunded_amount_numeric = payment.amount_numeric
    session.add(
        OrderTransitionModel(
            order_id=order.id,
            from_status=current.value,
            to_status=target.value,
            actor_user_id=actor_user_id,
            reason=reason,
        )
    )
    session.flush()
    from app.domain.enums import AutomationTrigger
    from app.services.automations import dispatch_automation_event

    dispatch_automation_event(
        session,
        store_id,
        AutomationTrigger.ORDER_STATUS_CHANGED,
        {
            "order_id": order.id,
            "customer_id": order.customer_id,
            "conversation_id": order.conversation_id or 0,
            "from_status": current.value,
            "to_status": target.value,
            "total": format(order.total_numeric, "f"),
        },
        f"order:{order.id}:{target.value}",
    )
    return order_out(session, store_id, order.id)


def create_order_checkout(
    session: Session,
    store_id: str,
    order_id: int,
    actor_user_id: str | None,
    public_base_url: str,
    secret_key: str,
    provider: PaymentProvider,
) -> CheckoutLink:
    order = _order_row(session, store_id, order_id)
    if order.status == OrderStatus.DRAFT.value:
        transition_order(
            session,
            store_id,
            order.id,
            OrderStatus.PENDING,
            actor_user_id=actor_user_id,
            reason=f"{provider.name}_checkout_created",
        )
        order = _order_row(session, store_id, order_id)
    elif order.status not in {OrderStatus.PENDING.value, OrderStatus.CONFIRMED.value}:
        raise ConflictError("Checkout is only available for draft, pending, or confirmed orders")
    now = datetime.now(UTC)
    existing = session.scalar(
        select(PaymentTransactionModel)
        .where(
            PaymentTransactionModel.order_id == order.id,
            PaymentTransactionModel.store_id == store_id,
            PaymentTransactionModel.provider == provider.name,
            PaymentTransactionModel.status.in_(("creating", "pending", "awaiting_cash")),
        )
        .order_by(PaymentTransactionModel.id.desc())
    )
    if (
        existing is not None
        and existing.checkout_url
        and (existing.expires_at is None or _utc(existing.expires_at) > now)
    ):
        return CheckoutLink(
            provider=existing.provider,
            url=existing.checkout_url,
            expires_at=existing.expires_at or now + timedelta(hours=1),
        )
    transaction = PaymentTransactionModel(
        store_id=store_id,
        order_id=order.id,
        provider=provider.name,
        status="creating",
        amount_numeric=order.total_numeric,
        currency=order.currency.upper(),
    )
    session.add(transaction)
    session.flush()
    amount_minor = int((order.total_numeric * 100).quantize(Decimal("1")))
    created = provider.create_checkout(
        order.id,
        store_id,
        amount_minor,
        order.currency,
        f"Order #{order.id}",
        str(transaction.id),
        public_base_url,
        secret_key,
    )
    transaction.checkout_session_id = created.checkout_session_id
    transaction.checkout_url = created.link.url
    transaction.expires_at = created.link.expires_at
    transaction.status = "awaiting_cash" if provider.name == "cod" else "pending"
    order.payment_status = transaction.status
    if created.checkout_session_id:
        order.provider_references_json = {
            **order.provider_references_json,
            provider.name: created.checkout_session_id,
        }
    if provider.name == "cod" and order.status == OrderStatus.PENDING.value:
        transition_order(
            session,
            store_id,
            order.id,
            OrderStatus.CONFIRMED,
            actor_user_id=actor_user_id,
            reason="cash_on_delivery_confirmed",
        )
    session.flush()
    return created.link


def create_demo_checkout(
    session: Session,
    store_id: str,
    order_id: int,
    actor_user_id: str | None,
    public_base_url: str,
    secret_key: str,
    provider: PaymentProvider,
) -> CheckoutLink:
    return create_order_checkout(
        session,
        store_id,
        order_id,
        actor_user_id,
        public_base_url,
        secret_key,
        provider,
    )


def confirm_demo_checkout(
    session: Session,
    order_id: int,
    token: str,
    secret_key: str,
    provider: PaymentProvider,
) -> OrderOut:
    store_id = provider.verify_checkout(order_id, token, secret_key)
    order = _order_row(session, store_id, order_id)
    if order.status == OrderStatus.PAID.value:
        return order_out(session, store_id, order_id)
    if order.status != OrderStatus.PENDING.value:
        raise ConflictError("Order is not awaiting demo payment")
    transition_order(
        session,
        store_id,
        order_id,
        OrderStatus.CONFIRMED,
        actor_user_id=None,
        reason="demo_checkout_confirmed",
    )
    return transition_order(
        session,
        store_id,
        order_id,
        OrderStatus.PAID,
        actor_user_id=None,
        reason="demo_payment_succeeded",
    )


def _claim_stripe_payment_event(session: Session, event: StripeEvent) -> bool:
    try:
        with session.begin_nested():
            session.add(
                StripeEventModel(
                    scope="payments",
                    event_id=event.event_id,
                    event_type=event.event_type,
                    livemode=event.livemode,
                    account_id=event.account_id,
                )
            )
            session.flush()
    except IntegrityError:
        return False
    return True


def _event_metadata(data: dict[str, object]) -> dict[str, object]:
    metadata = data.get("metadata")
    return dict(metadata) if isinstance(metadata, dict) else {}


def _event_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _transaction_for_checkout(
    session: Session,
    data: dict[str, object],
) -> PaymentTransactionModel:
    checkout_id = _event_string(data.get("id"))
    metadata = _event_metadata(data)
    try:
        order_id = int(str(metadata.get("order_id", "")))
    except ValueError as exc:
        raise ConflictError("Stripe payment metadata is incomplete") from exc
    store_id = _event_string(metadata.get("store_id"))
    row = session.scalar(
        select(PaymentTransactionModel).where(
            PaymentTransactionModel.checkout_session_id == checkout_id,
            PaymentTransactionModel.order_id == order_id,
            PaymentTransactionModel.store_id == store_id,
            PaymentTransactionModel.provider == "stripe",
        )
    )
    if row is None:
        raise NotFoundError(details={"entity": "payment_transaction"})
    return row


def _mark_order_paid(
    session: Session,
    transaction: PaymentTransactionModel,
) -> None:
    order = _order_row(session, transaction.store_id, transaction.order_id, lock=True)
    if order.status == OrderStatus.PAID.value:
        return
    if order.status == OrderStatus.PENDING.value:
        transition_order(
            session,
            order.store_id,
            order.id,
            OrderStatus.CONFIRMED,
            actor_user_id=None,
            reason="stripe_payment_confirmed",
        )
        order = _order_row(session, order.store_id, order.id, lock=True)
    if order.status != OrderStatus.CONFIRMED.value:
        raise ConflictError(
            "Paid order is in an incompatible state",
            details={"order_id": order.id, "status": order.status},
        )
    transition_order(
        session,
        order.store_id,
        order.id,
        OrderStatus.PAID,
        actor_user_id=None,
        reason="stripe_payment_succeeded",
    )


def _minor_amount(value: Decimal) -> int:
    return int((value * 100).quantize(Decimal("1")))


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def handle_payment_webhook(
    session: Session,
    provider: PaymentProvider,
    body: bytes,
    signature_header: str,
) -> bool:
    event = provider.verify_event(body, signature_header)
    if not _claim_stripe_payment_event(session, event):
        return False
    event_time = datetime.fromtimestamp(event.created, tz=UTC)
    data: dict[str, object] = dict(event.data)
    if event.event_type in {
        "checkout.session.completed",
        "checkout.session.async_payment_succeeded",
    }:
        if data.get("mode") not in {None, "payment"}:
            return True
        transaction = _transaction_for_checkout(session, data)
        if transaction.last_provider_event_at and event_time < _utc(
            transaction.last_provider_event_at
        ):
            return True
        payment_status = _event_string(data.get("payment_status"))
        if event.event_type == "checkout.session.completed" and payment_status not in {
            "paid",
            "no_payment_required",
        }:
            return True
        amount_total = data.get("amount_total")
        currency = _event_string(data.get("currency"))
        if amount_total != _minor_amount(transaction.amount_numeric) or (
            currency and currency.upper() != transaction.currency.upper()
        ):
            raise ConflictError("Stripe payment amount does not match the order")
        transaction.payment_intent_id = _event_string(data.get("payment_intent"))
        transaction.status = "paid"
        transaction.last_provider_event_at = event_time
        _mark_order_paid(session, transaction)
    elif event.event_type in {
        "checkout.session.async_payment_failed",
        "checkout.session.expired",
    }:
        transaction = _transaction_for_checkout(session, data)
        transaction.status = (
            "expired" if event.event_type == "checkout.session.expired" else "failed"
        )
        transaction.last_provider_event_at = event_time
        order = _order_row(session, transaction.store_id, transaction.order_id)
        order.payment_status = transaction.status
        if event.event_type == "checkout.session.expired" and order.status == "pending":
            transition_order(
                session,
                order.store_id,
                order.id,
                OrderStatus.CANCELLED,
                actor_user_id=None,
                reason="stripe_checkout_expired",
            )
    elif event.event_type == "charge.refunded":
        payment_intent_id = _event_string(data.get("payment_intent"))
        refund_transaction = session.scalar(
            select(PaymentTransactionModel).where(
                PaymentTransactionModel.provider == "stripe",
                PaymentTransactionModel.payment_intent_id == payment_intent_id,
            )
        )
        if refund_transaction is None:
            raise NotFoundError(details={"entity": "payment_transaction"})
        amount_refunded = data.get("amount_refunded")
        if not isinstance(amount_refunded, int):
            raise ConflictError("Stripe refund amount is missing")
        refund_transaction.refunded_amount_numeric = Decimal(amount_refunded) / Decimal(100)
        refund_transaction.last_provider_event_at = event_time
        if amount_refunded >= _minor_amount(refund_transaction.amount_numeric):
            refund_transaction.status = "refunded"
            order = _order_row(
                session,
                refund_transaction.store_id,
                refund_transaction.order_id,
            )
            if OrderStatus.REFUNDED in LEGAL_TRANSITIONS[OrderStatus(order.status)]:
                transition_order(
                    session,
                    order.store_id,
                    order.id,
                    OrderStatus.REFUNDED,
                    actor_user_id=None,
                    reason="stripe_refund_completed",
                )
        else:
            refund_transaction.status = "partially_refunded"
            partial_order = _order_row(
                session,
                refund_transaction.store_id,
                refund_transaction.order_id,
            )
            partial_order.payment_status = "partially_refunded"
    session.flush()
    return True


STATUS_MESSAGES: dict[OrderStatus, str] = {
    OrderStatus.CONFIRMED: "تم تأكيد طلبك بنجاح.",
    OrderStatus.PAID: "تم تسجيل الدفع للطلب.",
    OrderStatus.PROCESSING: "طلبك قيد التجهيز الآن.",
    OrderStatus.SHIPPED: "تم شحن طلبك وهو في الطريق إليك.",
    OrderStatus.DELIVERED: "تم تسليم طلبك. نتمنى أن تنال التجربة رضاك.",
    OrderStatus.CANCELLED: "تم إلغاء الطلب.",
    OrderStatus.REFUNDED: "تم تسجيل استرداد قيمة الطلب.",
}


def notify_order_status(
    session: Session, store_id: str, order_id: int, target: OrderStatus
) -> None:
    order = _order_row(session, store_id, order_id)
    if order.conversation_id is None or target not in STATUS_MESSAGES:
        return
    conversation = session.scalar(
        select(ConversationModel).where(
            ConversationModel.id == order.conversation_id,
            ConversationModel.store_id == store_id,
        )
    )
    if conversation is None:
        return
    queue_outbound_message(
        session,
        store_id=store_id,
        conversation=conversation,
        text=f"{STATUS_MESSAGES[target]} رقم الطلب: #{order.id}",
    )


def schedule_post_delivery(session: Session, store_id: str, order_id: int) -> None:
    enqueue_job(
        session,
        job_type="orders.review_request",
        store_id=store_id,
        payload={"store_id": store_id, "order_id": order_id},
        run_at=datetime.now(UTC) + timedelta(days=1),
        dedup_key=f"order-review:{order_id}",
    )
    enqueue_job(
        session,
        job_type="orders.repurchase_suggestion",
        store_id=store_id,
        payload={"store_id": store_id, "order_id": order_id},
        run_at=datetime.now(UTC) + timedelta(days=30),
        dedup_key=f"order-repurchase:{order_id}",
    )


def _post_delivery_message(session: Session, payload: dict[str, object], text: str) -> None:
    store_id = str(payload["store_id"])
    order_id = int(str(payload["order_id"]))
    order = _order_row(session, store_id, order_id)
    if order.status != OrderStatus.DELIVERED.value or order.conversation_id is None:
        return
    conversation = session.get(ConversationModel, order.conversation_id)
    if conversation is None:
        return
    try:
        queue_outbound_message(
            session,
            store_id=store_id,
            conversation=conversation,
            text=text,
        )
    except ConflictError:
        return


@job_handler("orders.review_request")
def review_request_job(session: Session, payload: dict[str, object]) -> None:
    _post_delivery_message(
        session,
        payload,
        "يهمنا رأيك في طلبك الأخير. كيف كانت تجربتك؟",
    )


@job_handler("orders.repurchase_suggestion")
def repurchase_job(session: Session, payload: dict[str, object]) -> None:
    _post_delivery_message(
        session,
        payload,
        "هل تحتاج إعادة طلب أحد منتجات طلبك السابق؟ يمكننا تجهيزها لك.",
    )
