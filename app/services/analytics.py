"""Real, tenant-scoped operational analytics over first-party data."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    AIUsageRecordModel,
    AutomationRunModel,
    ChannelModel,
    ContentItemModel,
    ConversationModel,
    CustomerModel,
    EventModel,
    MessageModel,
    OpportunityModel,
    OrderItemModel,
    OrderModel,
)
from app.domain.enums import MessageDirection, OpportunityStatus, OrderStatus
from app.domain.models import (
    AnalyticsAgentMetric,
    AnalyticsProductMetric,
    AnalyticsSnapshot,
)


def analytics_snapshot(
    session: Session,
    store_id: str,
    *,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    channel: str | None = None,
) -> AnalyticsSnapshot:
    end = period_end or datetime.now(UTC)
    start = period_start or end - timedelta(days=30)
    conversation_statement = (
        select(ConversationModel)
        .join(ChannelModel, ConversationModel.channel_id == ChannelModel.id)
        .where(
            ConversationModel.store_id == store_id,
            ConversationModel.created_at >= start,
            ConversationModel.created_at <= end,
        )
    )
    if channel:
        conversation_statement = conversation_statement.where(ChannelModel.channel_type == channel)
    conversations = session.scalars(conversation_statement).all()
    response_seconds: list[float] = []
    for conversation in conversations:
        messages = session.scalars(
            select(MessageModel)
            .where(MessageModel.conversation_id == conversation.id)
            .order_by(MessageModel.created_at, MessageModel.id)
        ).all()
        inbound_at = next(
            (
                message.created_at
                for message in messages
                if message.direction == MessageDirection.INBOUND.value
            ),
            None,
        )
        outbound_at = next(
            (
                message.created_at
                for message in messages
                if message.direction == MessageDirection.OUTBOUND.value
                and (inbound_at is None or message.created_at >= inbound_at)
            ),
            None,
        )
        if inbound_at is not None and outbound_at is not None:
            response_seconds.append((outbound_at - inbound_at).total_seconds())
    resolved = [
        row
        for row in conversations
        if row.status == "resolved" and row.updated_at >= row.created_at
    ]
    resolution_seconds = [(row.updated_at - row.created_at).total_seconds() for row in resolved]
    customers = session.scalars(
        select(CustomerModel).where(
            CustomerModel.store_id == store_id,
            CustomerModel.lead_score > 0,
            CustomerModel.last_seen_at >= start,
            CustomerModel.last_seen_at <= end,
        )
    ).all()
    order_statement = select(OrderModel).where(
        OrderModel.store_id == store_id,
        OrderModel.created_at >= start,
        OrderModel.created_at <= end,
    )
    if channel:
        order_statement = (
            order_statement.join(
                ConversationModel,
                OrderModel.conversation_id == ConversationModel.id,
            )
            .join(ChannelModel, ConversationModel.channel_id == ChannelModel.id)
            .where(ChannelModel.channel_type == channel)
        )
    orders = session.scalars(order_statement).all()
    revenue_statuses = {
        OrderStatus.PAID.value,
        OrderStatus.PROCESSING.value,
        OrderStatus.SHIPPED.value,
        OrderStatus.DELIVERED.value,
    }
    revenue_orders = [row for row in orders if row.status in revenue_statuses]
    attributed_revenue = sum(
        (row.total_numeric for row in revenue_orders if row.conversation_id),
        Decimal("0"),
    )
    order_channels: dict[str, int] = {}
    for order in orders:
        if order.conversation_id is None:
            key = "direct"
        else:
            key = (
                session.scalar(
                    select(ChannelModel.channel_type)
                    .join(
                        ConversationModel,
                        ConversationModel.channel_id == ChannelModel.id,
                    )
                    .where(ConversationModel.id == order.conversation_id)
                )
                or "unknown"
            )
        order_channels[str(key)] = order_channels.get(str(key), 0) + 1
    product_rows = session.execute(
        select(
            OrderItemModel.product_id,
            OrderItemModel.product_name,
            func.sum(OrderItemModel.quantity),
            func.sum(OrderItemModel.line_total_numeric),
        )
        .join(OrderModel, OrderItemModel.order_id == OrderModel.id)
        .where(
            OrderModel.store_id == store_id,
            OrderModel.created_at >= start,
            OrderModel.created_at <= end,
            OrderModel.status.in_(revenue_statuses),
        )
        .group_by(OrderItemModel.product_id, OrderItemModel.product_name)
        .order_by(func.sum(OrderItemModel.line_total_numeric).desc())
        .limit(10)
    ).all()
    automation_runs = session.scalars(
        select(AutomationRunModel).where(
            AutomationRunModel.store_id == store_id,
            AutomationRunModel.created_at >= start,
            AutomationRunModel.created_at <= end,
        )
    ).all()
    ai_rows = session.scalars(
        select(AIUsageRecordModel).where(
            AIUsageRecordModel.store_id == store_id,
            AIUsageRecordModel.created_at >= start,
            AIUsageRecordModel.created_at <= end,
        )
    ).all()
    ai_cost = (
        sum((row.cost_numeric or Decimal("0") for row in ai_rows), Decimal("0"))
        if ai_rows and all(row.cost_numeric is not None for row in ai_rows)
        else None
    )
    agent_rows = session.execute(
        select(MessageModel.sender_user_id, func.count(MessageModel.id))
        .join(ConversationModel, MessageModel.conversation_id == ConversationModel.id)
        .where(
            ConversationModel.store_id == store_id,
            MessageModel.direction == MessageDirection.OUTBOUND.value,
            MessageModel.sender_user_id.is_not(None),
            MessageModel.created_at >= start,
            MessageModel.created_at <= end,
        )
        .group_by(MessageModel.sender_user_id)
    ).all()
    opportunity_rows = session.scalars(
        select(OpportunityModel).where(
            OpportunityModel.store_id == store_id,
            OpportunityModel.detected_at >= start,
            OpportunityModel.detected_at <= end,
        )
    ).all()
    content_published = (
        session.scalar(
            select(func.count(ContentItemModel.id)).where(
                ContentItemModel.store_id == store_id,
                ContentItemModel.status == "published",
                ContentItemModel.published_at >= start,
                ContentItemModel.published_at <= end,
            )
        )
        or 0
    )
    engagements = (
        session.scalar(
            select(func.count(EventModel.id)).where(
                EventModel.store_id == store_id,
                EventModel.event_type.in_(["content_engagement", "content_click"]),
                EventModel.created_at >= start,
                EventModel.created_at <= end,
            )
        )
        or 0
    )
    successful_runs = sum(row.status == "succeeded" for row in automation_runs)
    paid_count = len(revenue_orders)
    return AnalyticsSnapshot(
        period_start=start,
        period_end=end,
        channel=channel,
        conversation_volume=len(conversations),
        first_response_minutes=(
            Decimal(str(sum(response_seconds) / len(response_seconds) / 60)).quantize(
                Decimal("0.01")
            )
            if response_seconds
            else None
        ),
        resolution_minutes=(
            Decimal(str(sum(resolution_seconds) / len(resolution_seconds) / 60)).quantize(
                Decimal("0.01")
            )
            if resolution_seconds
            else None
        ),
        leads=len(customers),
        conversion_rate=(
            Decimal(paid_count * 100 / len(conversations)).quantize(Decimal("0.01"))
            if conversations
            else Decimal("0")
        ),
        attributed_revenue=attributed_revenue,
        recovered_revenue=sum(
            (row.realized_revenue_numeric for row in opportunity_rows),
            Decimal("0"),
        ),
        orders_by_channel=order_channels,
        top_products=[
            AnalyticsProductMetric(
                product_id=str(product_id),
                name=str(name),
                quantity=int(quantity or 0),
                revenue=Decimal(revenue or 0),
            )
            for product_id, name, quantity, revenue in product_rows
        ],
        content_published=int(content_published),
        content_engagements=int(engagements),
        automation_runs=len(automation_runs),
        automation_success_rate=(
            Decimal(successful_runs * 100 / len(automation_runs)).quantize(Decimal("0.01"))
            if automation_runs
            else Decimal("0")
        ),
        ai_operations=len(ai_rows),
        ai_cost=ai_cost,
        agent_performance=[
            AnalyticsAgentMetric(user_id=str(user_id), messages_sent=int(count))
            for user_id, count in agent_rows
        ],
        funnel={
            "conversations": len(conversations),
            "leads": len(customers),
            "orders": len(orders),
            "paid": paid_count,
            "won_opportunities": sum(
                row.status == OpportunityStatus.WON.value for row in opportunity_rows
            ),
        },
    )
