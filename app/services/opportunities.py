"""Rule-based revenue opportunity detection and auditable decisions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    ChannelModel,
    ConversationModel,
    CustomerModel,
    EventModel,
    OpportunityActionModel,
    OpportunityModel,
    OrderItemModel,
    OrderModel,
    ProductModel,
)
from app.domain.enums import OpportunityStatus, OrderStatus, ProductStatus
from app.domain.errors import ConflictError, NotFoundError
from app.domain.models import OpportunityDashboard, OpportunityOut
from app.services.job_queue import enqueue_job, job_handler


def _out(row: OpportunityModel) -> OpportunityOut:
    return OpportunityOut(
        id=row.id,
        opportunity_type=row.opportunity_type,
        customer_id=row.customer_id,
        related_product_ids=list(row.related_product_ids_json),
        reason=row.reason,
        expected_revenue=row.expected_revenue_numeric,
        realized_revenue=row.realized_revenue_numeric,
        confidence=row.confidence,
        suggested_action=row.suggested_action,
        channel=row.channel,
        message=row.message,
        status=OpportunityStatus(row.status),
        detected_at=row.detected_at,
    )


def _add(
    session: Session,
    *,
    store_id: str,
    opportunity_type: str,
    dedup_key: str,
    reason: str,
    expected_revenue: Decimal,
    confidence: int,
    suggested_action: str,
    message: str,
    customer_id: int | None = None,
    product_ids: list[str] | None = None,
    channel: str | None = None,
) -> bool:
    exists = session.scalar(
        select(OpportunityModel.id).where(
            OpportunityModel.store_id == store_id,
            OpportunityModel.dedup_key == dedup_key,
        )
    )
    if exists is not None:
        return False
    row = OpportunityModel(
        store_id=store_id,
        customer_id=customer_id,
        opportunity_type=opportunity_type,
        dedup_key=dedup_key,
        related_product_ids_json=product_ids or [],
        reason=reason,
        expected_revenue_numeric=expected_revenue,
        realized_revenue_numeric=Decimal("0"),
        confidence=confidence,
        suggested_action=suggested_action,
        channel=channel,
        message=message,
        status=OpportunityStatus.NEW.value,
    )
    session.add(row)
    session.flush()
    from app.domain.enums import AutomationTrigger
    from app.services.automations import dispatch_automation_event

    event = {
        "opportunity_id": row.id,
        "customer_id": customer_id or 0,
        "opportunity_type": opportunity_type,
        "expected_revenue": format(expected_revenue, "f"),
    }
    dispatch_automation_event(
        session,
        store_id,
        AutomationTrigger.NEW_OPPORTUNITY,
        event,
        f"opportunity:{row.id}",
    )
    if opportunity_type == "abandoned_cart":
        dispatch_automation_event(
            session,
            store_id,
            AutomationTrigger.ABANDONED_CART,
            event,
            f"abandoned:{row.id}",
        )
    elif opportunity_type == "low_stock":
        dispatch_automation_event(
            session,
            store_id,
            AutomationTrigger.LOW_STOCK,
            event,
            f"low-stock:{row.id}",
        )
    return True


def detect_opportunities(session: Session, store_id: str) -> int:
    """Run deterministic P0 detectors; repeated runs are deduplicated."""

    created = 0
    period = datetime.now(UTC).strftime("%Y-%m")
    low_stock = session.scalars(
        select(ProductModel).where(
            ProductModel.store_id == store_id,
            ProductModel.status == ProductStatus.ACTIVE.value,
            ProductModel.stock.between(1, 3),
        )
    ).all()
    for product in low_stock:
        created += _add(
            session,
            store_id=store_id,
            opportunity_type="low_stock",
            dedup_key=f"low-stock:{product.product_id}:{period}",
            reason=f"المخزون المتبقي {product.stock} وحدات فقط.",
            expected_revenue=product.price_numeric * product.stock,
            confidence=95,
            suggested_action="إنشاء حملة عاجلة للكمية المتبقية ومراجعة إعادة الطلب.",
            message=f"الكمية الأخيرة من {product.name} متاحة الآن.",
            product_ids=[product.product_id],
        )
    conversations = session.execute(
        select(ConversationModel, CustomerModel, ChannelModel)
        .join(CustomerModel, ConversationModel.customer_id == CustomerModel.id)
        .join(ChannelModel, ConversationModel.channel_id == ChannelModel.id)
        .where(
            ConversationModel.store_id == store_id,
            ConversationModel.last_inbound_at.is_not(None),
            ConversationModel.last_outbound_at.is_(None),
        )
    ).all()
    for conversation, customer, channel in conversations:
        consent = bool(customer.consent_json.get(channel.channel_type))
        if not consent:
            continue
        created += _add(
            session,
            store_id=store_id,
            opportunity_type="asked_no_reply",
            dedup_key=f"asked:{conversation.id}:{period}",
            reason="العميل بدأ محادثة ولم يحصل على متابعة بعد.",
            expected_revenue=Decimal("500"),
            confidence=70,
            suggested_action="مراجعة المحادثة وإرسال رد شخصي بعد الموافقة.",
            message="أهلًا، هل ما زلت تبحث عن المنتج المناسب؟ أقدر أساعدك.",
            customer_id=customer.id,
            channel=channel.channel_type,
        )
    created += _detect_behavior_events(session, store_id, period)
    created += _detect_slow_moving(session, store_id, period)
    created += _detect_repurchase_and_cross_sell(session, store_id, period)
    created += _detect_conversation_signals(session, store_id, period)
    created += _detect_content_signals(session, store_id, period)
    return created


def _detect_behavior_events(session: Session, store_id: str, period: str) -> int:
    created = 0
    rows = session.scalars(
        select(EventModel).where(
            EventModel.store_id == store_id,
            EventModel.event_type.in_(
                ["product_view", "add_to_cart", "checkout_started", "purchase"]
            ),
        )
    ).all()
    by_session: dict[str, list[EventModel]] = {}
    for row in rows:
        by_session.setdefault(row.session_key, []).append(row)
    for session_key, events in by_session.items():
        types = {event.event_type for event in events}
        products = [event.product_id for event in events if event.product_id]
        customer_id = next(
            (event.customer_id for event in events if event.customer_id is not None),
            None,
        )
        for product_id in sorted(set(products)):
            views = sum(
                event.event_type == "product_view" and event.product_id == product_id
                for event in events
            )
            product = session.scalar(
                select(ProductModel).where(
                    ProductModel.store_id == store_id,
                    ProductModel.product_id == product_id,
                )
            )
            if product is not None and views >= 3:
                created += _add(
                    session,
                    store_id=store_id,
                    opportunity_type="repeated_product_views",
                    dedup_key=f"repeat-view:{session_key}:{product_id}:{period}",
                    reason=f"تمت مشاهدة {product.name} عدد {views} مرات.",
                    expected_revenue=product.price_numeric,
                    confidence=80,
                    suggested_action="اعرض مساعدة شخصية أو إجابة عن الاعتراض المتبقي.",
                    message=f"هل تحتاج مساعدة قبل اختيار {product.name}؟",
                    customer_id=customer_id,
                    product_ids=[product_id],
                    channel="webchat",
                )
        if {"add_to_cart", "checkout_started"} & types and "purchase" not in types:
            expected = sum(
                (
                    product.price_numeric
                    for product in session.scalars(
                        select(ProductModel).where(
                            ProductModel.store_id == store_id,
                            ProductModel.product_id.in_(set(products)),
                        )
                    )
                ),
                Decimal("0"),
            )
            created += _add(
                session,
                store_id=store_id,
                opportunity_type="abandoned_cart",
                dedup_key=f"abandoned:{session_key}:{period}",
                reason="بدأ العميل السلة أو الدفع دون تسجيل شراء.",
                expected_revenue=expected,
                confidence=88,
                suggested_action="أرسل تذكيرًا بالمحتويات بعد الموافقة.",
                message="منتجاتك ما زالت محفوظة. هل واجهتك مشكلة في إكمال الطلب؟",
                customer_id=customer_id,
                product_ids=sorted(set(products)),
                channel="webchat",
            )
    return created


def _detect_slow_moving(session: Session, store_id: str, period: str) -> int:
    sold_ids = set(
        session.scalars(
            select(OrderItemModel.product_id)
            .join(OrderModel, OrderItemModel.order_id == OrderModel.id)
            .where(
                OrderModel.store_id == store_id,
                OrderModel.status.in_(
                    [
                        OrderStatus.PAID.value,
                        OrderStatus.PROCESSING.value,
                        OrderStatus.SHIPPED.value,
                        OrderStatus.DELIVERED.value,
                    ]
                ),
                OrderModel.updated_at >= datetime.now(UTC) - timedelta(days=30),
            )
        )
    )
    created = 0
    products = session.scalars(
        select(ProductModel).where(
            ProductModel.store_id == store_id,
            ProductModel.status == ProductStatus.ACTIVE.value,
            ProductModel.stock >= 10,
        )
    ).all()
    for product in products:
        if product.product_id in sold_ids:
            continue
        created += _add(
            session,
            store_id=store_id,
            opportunity_type="slow_moving_product",
            dedup_key=f"slow:{product.product_id}:{period}",
            reason="لا توجد مبيعات مسجلة لهذا المنتج خلال آخر 30 يومًا.",
            expected_revenue=product.price_numeric * min(product.stock, 5),
            confidence=75,
            suggested_action="أنشئ محتوى تعليميًا أو Bundle بدل خصم عشوائي.",
            message=f"اكتشف استخدامات {product.name} ومميزاته العملية.",
            product_ids=[product.product_id],
        )
    return created


def _detect_repurchase_and_cross_sell(session: Session, store_id: str, period: str) -> int:
    created = 0
    delivered = session.scalars(
        select(OrderModel).where(
            OrderModel.store_id == store_id,
            OrderModel.status == OrderStatus.DELIVERED.value,
        )
    ).all()
    for order in delivered:
        items = session.scalars(
            select(OrderItemModel).where(OrderItemModel.order_id == order.id)
        ).all()
        product_ids = [item.product_id for item in items]
        if order.updated_at.replace(tzinfo=UTC) <= datetime.now(UTC) - timedelta(days=30):
            created += _add(
                session,
                store_id=store_id,
                opportunity_type="repurchase_due",
                dedup_key=f"repurchase:{order.id}:{period}",
                reason="مر أكثر من 30 يومًا على طلب تم تسليمه.",
                expected_revenue=order.total_numeric,
                confidence=72,
                suggested_action="اقترح إعادة الطلب دون افتراض حاجة العميل.",
                message="هل حان وقت إعادة طلب أحد منتجات طلبك السابق؟",
                customer_id=order.customer_id,
                product_ids=product_ids,
            )
        original_products = session.scalars(
            select(ProductModel).where(
                ProductModel.store_id == store_id,
                ProductModel.product_id.in_(product_ids),
            )
        ).all()
        categories = {product.category for product in original_products}
        candidate = session.scalar(
            select(ProductModel).where(
                ProductModel.store_id == store_id,
                ProductModel.status == ProductStatus.ACTIVE.value,
                ProductModel.stock > 0,
                ProductModel.category.in_(categories),
                ProductModel.product_id.not_in(product_ids),
            )
        )
        if candidate is not None:
            created += _add(
                session,
                store_id=store_id,
                opportunity_type="cross_sell",
                dedup_key=f"cross-sell:{order.id}:{candidate.product_id}:{period}",
                reason="منتج مكمل متاح ضمن فئة طلب العميل السابق.",
                expected_revenue=candidate.price_numeric,
                confidence=65,
                suggested_action="اعرض المنتج المكمل كاقتراح اختياري.",
                message=f"قد يناسبك أيضًا {candidate.name} مع طلبك السابق.",
                customer_id=order.customer_id,
                product_ids=[*product_ids, candidate.product_id],
            )
    return created


def _detect_conversation_signals(session: Session, store_id: str, period: str) -> int:
    created = 0
    rows = session.execute(
        select(ConversationModel, CustomerModel, ChannelModel)
        .join(CustomerModel, ConversationModel.customer_id == CustomerModel.id)
        .join(ChannelModel, ConversationModel.channel_id == ChannelModel.id)
        .where(ConversationModel.store_id == store_id)
    ).all()
    for conversation, customer, channel in rows:
        preview = conversation.last_message_preview.casefold()
        common = {
            "session": session,
            "store_id": store_id,
            "customer_id": customer.id,
            "channel": channel.channel_type,
            "expected_revenue": Decimal("500"),
            "confidence": 68,
        }
        if (
            any(word in preview for word in ("السعر", "غالي", "price"))
            and conversation.last_outbound_at
        ):
            created += _add(
                **common,
                opportunity_type="quiet_after_price",
                dedup_key=f"price-quiet:{conversation.id}:{period}",
                reason="آخر سياق للمحادثة مرتبط بالسعر ولم ينتج عنه طلب.",
                suggested_action="اشرح القيمة أو اقترح بديلًا داخل الميزانية.",
                message="أقدر أقترح بديلًا مناسبًا لميزانيتك بدون التنازل عن احتياجك.",
            )
        if any(word in preview for word in ("ولا", "مقارنة", "أنهي", "which")):
            created += _add(
                **common,
                opportunity_type="undecided_between_products",
                dedup_key=f"undecided:{conversation.id}:{period}",
                reason="العميل يقارن بين اختيارات ولم يحسم القرار.",
                suggested_action="أرسل مقارنة قصيرة مبنية على الاستخدام.",
                message="أقدر ألخص الفرق بين الاختيارات حسب استخدامك الأساسي.",
            )
        if any(word in preview for word in ("خلص", "غير متوفر", "out of stock")):
            created += _add(
                **common,
                opportunity_type="needs_available_alternative",
                dedup_key=f"alternative:{conversation.id}:{period}",
                reason="المحادثة تشير إلى منتج غير متاح.",
                suggested_action="اقترح بديلًا متاحًا من نفس الفئة والسعر.",
                message="يوجد بديل متاح قريب في المواصفات والسعر.",
            )
    return created


def _detect_content_signals(session: Session, store_id: str, period: str) -> int:
    created = 0
    events = session.scalars(
        select(EventModel).where(
            EventModel.store_id == store_id,
            EventModel.event_type.in_(["content_engagement", "content_click"]),
        )
    ).all()
    by_content: dict[str, list[EventModel]] = {}
    for event in events:
        content_id = str(event.payload_json.get("content_id", ""))
        if content_id:
            by_content.setdefault(content_id, []).append(event)
    for content_id, content_events in by_content.items():
        purchases = sum(event.payload_json.get("converted") is True for event in content_events)
        if len(content_events) >= 10:
            created += _add(
                session,
                store_id=store_id,
                opportunity_type=(
                    "high_performing_post_reuse" if purchases else "engagement_without_sales"
                ),
                dedup_key=f"content:{content_id}:{period}",
                reason=f"المحتوى سجل {len(content_events)} تفاعلًا و{purchases} تحويلات.",
                expected_revenue=Decimal("1000") if purchases else Decimal("500"),
                confidence=78,
                suggested_action=(
                    "أعد استخدام زاوية المحتوى الناجحة."
                    if purchases
                    else "عدّل العرض وCTA بدل زيادة التفاعل فقط."
                ),
                message="",
            )
    return created


def list_opportunities(session: Session, store_id: str) -> list[OpportunityOut]:
    rows = session.scalars(
        select(OpportunityModel)
        .where(OpportunityModel.store_id == store_id)
        .order_by(
            OpportunityModel.expected_revenue_numeric.desc(),
            OpportunityModel.detected_at.desc(),
        )
    ).all()
    return [_out(row) for row in rows]


def opportunity_dashboard(session: Session, store_id: str) -> OpportunityDashboard:
    opportunities = list_opportunities(session, store_id)
    return OpportunityDashboard(
        potential_revenue=sum(
            (
                item.expected_revenue
                for item in opportunities
                if item.status not in {OpportunityStatus.REJECTED, OpportunityStatus.WON}
            ),
            Decimal("0"),
        ),
        recovered_revenue=sum(
            (item.realized_revenue for item in opportunities),
            Decimal("0"),
        ),
        new_count=sum(item.status == OpportunityStatus.NEW for item in opportunities),
        awaiting_approval_count=sum(
            item.status == OpportunityStatus.AWAITING_APPROVAL for item in opportunities
        ),
        executed_count=sum(item.status == OpportunityStatus.EXECUTED for item in opportunities),
        won_count=sum(item.status == OpportunityStatus.WON for item in opportunities),
        funnel={
            "opportunity": len(opportunities),
            "approved": sum(
                item.status
                in {
                    OpportunityStatus.AWAITING_APPROVAL,
                    OpportunityStatus.EXECUTED,
                    OpportunityStatus.WON,
                }
                for item in opportunities
            ),
            "executed": sum(
                item.status in {OpportunityStatus.EXECUTED, OpportunityStatus.WON}
                for item in opportunities
            ),
            "won": sum(item.status == OpportunityStatus.WON for item in opportunities),
        },
        top_opportunities=opportunities[:5],
    )


def decide_opportunity(
    session: Session,
    store_id: str,
    opportunity_id: int,
    decision: str,
    actor_user_id: str,
    realized_revenue: Decimal,
) -> OpportunityOut:
    row = session.scalar(
        select(OpportunityModel).where(
            OpportunityModel.id == opportunity_id,
            OpportunityModel.store_id == store_id,
        )
    )
    if row is None:
        raise NotFoundError(details={"entity": "opportunity", "id": opportunity_id})
    transitions = {
        "approve": (
            {OpportunityStatus.NEW.value},
            OpportunityStatus.AWAITING_APPROVAL.value,
        ),
        "execute": (
            {OpportunityStatus.AWAITING_APPROVAL.value},
            OpportunityStatus.EXECUTED.value,
        ),
        "reject": (
            {OpportunityStatus.NEW.value, OpportunityStatus.AWAITING_APPROVAL.value},
            OpportunityStatus.REJECTED.value,
        ),
        "won": ({OpportunityStatus.EXECUTED.value}, OpportunityStatus.WON.value),
    }
    allowed, target = transitions[decision]
    if row.status not in allowed:
        raise ConflictError(
            "Illegal opportunity transition",
            details={"from": row.status, "decision": decision},
        )
    row.status = target
    if decision == "won":
        row.realized_revenue_numeric = realized_revenue.quantize(Decimal("0.01"))
    session.add(
        OpportunityActionModel(
            opportunity_id=row.id,
            action=decision,
            actor_user_id=actor_user_id,
            metadata_json={"realized_revenue": format(realized_revenue, "f")},
        )
    )
    session.flush()
    return _out(row)


def enqueue_opportunity_scan(session: Session, store_id: str) -> None:
    enqueue_job(
        session,
        job_type="opportunities.scan",
        store_id=store_id,
        payload={"store_id": store_id},
        dedup_key=f"opportunity-scan:{store_id}:{datetime.now(UTC):%Y%m%d%H}",
    )


@job_handler("opportunities.scan")
def scan_job(session: Session, payload: dict[str, Any]) -> None:
    detect_opportunities(session, str(payload["store_id"]))
