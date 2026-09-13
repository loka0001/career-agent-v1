"""Explainable customer scoring and practical segments from first-party data."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    ConversationModel,
    CustomerIdentityModel,
    CustomerModel,
    EventModel,
    OrderItemModel,
    OrderModel,
)
from app.domain.enums import OrderStatus
from app.domain.errors import NotFoundError
from app.domain.models import (
    CustomerIntelligence,
    CustomerSummary,
    CustomerTimelineEvent,
    RfmSnapshot,
    ScoreSignal,
)


def customer_intelligence(
    session: Session, store_id: str, customer_id: int
) -> CustomerIntelligence:
    customer = session.scalar(
        select(CustomerModel).where(
            CustomerModel.id == customer_id,
            CustomerModel.store_id == store_id,
            CustomerModel.merged_into_id.is_(None),
        )
    )
    if customer is None:
        raise NotFoundError(details={"entity": "customer", "id": customer_id})
    events = session.execute(
        select(EventModel.event_type, func.count(EventModel.id))
        .where(EventModel.store_id == store_id, EventModel.customer_id == customer.id)
        .group_by(EventModel.event_type)
    ).all()
    event_counts = {str(kind): int(count) for kind, count in events}
    completed = session.scalars(
        select(OrderModel).where(
            OrderModel.store_id == store_id,
            OrderModel.customer_id == customer.id,
            OrderModel.status.in_(
                [
                    OrderStatus.PAID.value,
                    OrderStatus.PROCESSING.value,
                    OrderStatus.SHIPPED.value,
                    OrderStatus.DELIVERED.value,
                ]
            ),
        )
    ).all()
    revenue = sum((order.total_numeric for order in completed), Decimal("0"))
    rules = [
        ("product_views", min(event_counts.get("product_view", 0), 10), 2, "مشاهدات المنتجات"),
        ("add_to_cart", min(event_counts.get("add_to_cart", 0), 3), 12, "إضافة للسلة"),
        ("checkout", min(event_counts.get("checkout_started", 0), 2), 18, "بدأ الدفع"),
        ("purchases", min(len(completed), 3), 20, "طلبات مدفوعة"),
    ]
    signals = [
        ScoreSignal(
            name=name,
            value=value,
            weight=weight,
            contribution=value * weight,
            explanation=explanation,
        )
        for name, value, weight, explanation in rules
        if value
    ]
    score = min(100, sum(signal.contribution for signal in signals))
    customer.lead_score = score
    days_inactive = max(0, (datetime.now(UTC) - customer.last_seen_at.replace(tzinfo=UTC)).days)
    segments: list[str] = []
    if len(completed) == 0:
        segments.append("new")
    if len(completed) >= 2:
        segments.append("repeat")
    if revenue >= Decimal("5000"):
        segments.append("vip")
    if score >= 50:
        segments.append("high-intent")
    if event_counts.get("add_to_cart", 0) > event_counts.get("purchase", 0):
        segments.append("abandoned-cart")
    if days_inactive >= 30:
        segments.append("lapsed")
    if customer.consent_json and not any(bool(value) for value in customer.consent_json.values()):
        segments.append("do-not-contact")
    product_rows = session.execute(
        select(OrderItemModel.product_id, func.sum(OrderItemModel.quantity))
        .join(OrderModel, OrderItemModel.order_id == OrderModel.id)
        .where(OrderModel.store_id == store_id, OrderModel.customer_id == customer.id)
        .group_by(OrderItemModel.product_id)
        .order_by(func.sum(OrderItemModel.quantity).desc())
        .limit(5)
    ).all()
    viewed_products = session.scalars(
        select(EventModel.product_id)
        .where(
            EventModel.store_id == store_id,
            EventModel.customer_id == customer.id,
            EventModel.event_type == "product_view",
            EventModel.product_id.is_not(None),
        )
        .distinct()
        .limit(5)
    ).all()
    preferred = [str(product_id) for product_id, _ in product_rows]
    for product_id in viewed_products:
        if product_id and product_id not in preferred:
            preferred.append(product_id)
    recency_score = (
        5
        if days_inactive <= 7
        else 4
        if days_inactive <= 30
        else 3
        if days_inactive <= 90
        else 2
        if days_inactive <= 180
        else 1
    )
    frequency_score = min(5, max(1, len(completed)))
    monetary_score = (
        5
        if revenue >= Decimal("10000")
        else 4
        if revenue >= Decimal("5000")
        else 3
        if revenue >= Decimal("2000")
        else 2
        if revenue > 0
        else 1
    )
    purchase_probability = min(
        95,
        score + (10 if event_counts.get("checkout_started", 0) else 0),
    )
    churn_risk = (
        "high"
        if completed and days_inactive >= 90
        else "medium"
        if completed and days_inactive >= 30
        else "low"
    )
    timeline: list[CustomerTimelineEvent] = []
    for event in session.scalars(
        select(EventModel)
        .where(EventModel.store_id == store_id, EventModel.customer_id == customer.id)
        .order_by(EventModel.created_at.desc())
        .limit(50)
    ):
        timeline.append(
            CustomerTimelineEvent(
                event_type=event.event_type,
                title=event.event_type.replace("_", " ").title(),
                detail=event.product_id or event.session_key,
                occurred_at=event.created_at,
            )
        )
    for order in completed:
        timeline.append(
            CustomerTimelineEvent(
                event_type="order",
                title=f"Order #{order.id}",
                detail=f"{order.status} · {format(order.total_numeric, 'f')} {order.currency}",
                occurred_at=order.updated_at,
            )
        )
    for conversation in session.scalars(
        select(ConversationModel)
        .where(
            ConversationModel.store_id == store_id,
            ConversationModel.customer_id == customer.id,
        )
        .order_by(ConversationModel.updated_at.desc())
        .limit(20)
    ):
        timeline.append(
            CustomerTimelineEvent(
                event_type="conversation",
                title=f"Conversation #{conversation.id}",
                detail=conversation.last_message_preview,
                occurred_at=conversation.updated_at,
            )
        )
    timeline.sort(key=lambda item: item.occurred_at, reverse=True)
    return CustomerIntelligence(
        customer=CustomerSummary(
            id=customer.id,
            display_name=customer.display_name,
            phone=customer.phone,
            email=customer.email,
            tags=list(customer.tags_json),
            lead_score=score,
            consent={key: bool(value) for key, value in customer.consent_json.items()},
            first_seen_at=customer.first_seen_at,
            last_seen_at=customer.last_seen_at,
        ),
        lead_score=score,
        score_signals=signals,
        segments=segments,
        completed_orders=len(completed),
        total_revenue=revenue,
        average_order_value=revenue / len(completed) if completed else Decimal("0"),
        days_since_last_activity=days_inactive,
        preferred_product_ids=preferred[:5],
        rfm=RfmSnapshot(
            recency_days=days_inactive,
            frequency=len(completed),
            monetary=revenue,
            recency_score=recency_score,
            frequency_score=frequency_score,
            monetary_score=monetary_score,
        ),
        purchase_probability=purchase_probability,
        churn_risk=churn_risk,
        timeline=timeline[:100],
    )


def list_customer_intelligence(session: Session, store_id: str) -> list[CustomerIntelligence]:
    ids = session.scalars(
        select(CustomerModel.id)
        .where(
            CustomerModel.store_id == store_id,
            CustomerModel.merged_into_id.is_(None),
        )
        .order_by(CustomerModel.last_seen_at.desc())
    ).all()
    return [customer_intelligence(session, store_id, customer_id) for customer_id in ids]


def merge_customers(
    session: Session, store_id: str, target_id: int, source_id: int
) -> CustomerIntelligence:
    if target_id == source_id:
        raise NotFoundError(details={"entity": "source_customer", "id": source_id})
    target = session.scalar(
        select(CustomerModel).where(
            CustomerModel.id == target_id,
            CustomerModel.store_id == store_id,
            CustomerModel.merged_into_id.is_(None),
        )
    )
    source = session.scalar(
        select(CustomerModel).where(
            CustomerModel.id == source_id,
            CustomerModel.store_id == store_id,
            CustomerModel.merged_into_id.is_(None),
        )
    )
    if target is None or source is None:
        raise NotFoundError(details={"entity": "customer"})
    for identity in session.scalars(
        select(CustomerIdentityModel).where(
            CustomerIdentityModel.store_id == store_id,
            CustomerIdentityModel.customer_id == source.id,
        )
    ):
        identity.customer_id = target.id
    session.query(ConversationModel).filter(
        ConversationModel.store_id == store_id,
        ConversationModel.customer_id == source.id,
    ).update({"customer_id": target.id})
    session.query(EventModel).filter(
        EventModel.store_id == store_id,
        EventModel.customer_id == source.id,
    ).update({"customer_id": target.id})
    session.query(OrderModel).filter(
        OrderModel.store_id == store_id,
        OrderModel.customer_id == source.id,
    ).update({"customer_id": target.id})
    target.phone = target.phone or source.phone
    target.email = target.email or source.email
    target.tags_json = sorted(set(target.tags_json) | set(source.tags_json))
    keys = set(target.consent_json) | set(source.consent_json)
    target.consent_json = {
        key: bool(target.consent_json.get(key, True)) and bool(source.consent_json.get(key, True))
        for key in keys
    }
    target.first_seen_at = min(target.first_seen_at, source.first_seen_at)
    target.last_seen_at = max(target.last_seen_at, source.last_seen_at)
    source.merged_into_id = target.id
    session.flush()
    return customer_intelligence(session, store_id, target.id)
