"""Unified inbox reads: conversation lists, details, and mapping to contracts."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    ChannelModel,
    ConversationModel,
    CustomerModel,
    MessageModel,
)
from app.domain.enums import (
    ChannelType,
    ConversationPriority,
    ConversationStatus,
    MessageDirection,
    MessageSenderType,
    MessageStatus,
)
from app.domain.errors import NotFoundError
from app.domain.models import (
    ConversationDetail,
    ConversationSummary,
    CustomerSummary,
    MessageOut,
)


def _customer_summary(customer: CustomerModel) -> CustomerSummary:
    return CustomerSummary(
        id=customer.id,
        display_name=customer.display_name,
        phone=customer.phone,
        email=customer.email,
        tags=list(customer.tags_json),
        lead_score=customer.lead_score,
        consent={key: bool(value) for key, value in customer.consent_json.items()},
        first_seen_at=customer.first_seen_at,
        last_seen_at=customer.last_seen_at,
    )


def _sla_overdue(conversation: ConversationModel, now: datetime) -> bool:
    if conversation.status != ConversationStatus.OPEN.value:
        return False
    if conversation.sla_due_at is None:
        return False
    due = conversation.sla_due_at
    if due.tzinfo is None:
        due = due.replace(tzinfo=UTC)
    return due < now


def _summary(
    conversation: ConversationModel,
    channel: ChannelModel,
    customer: CustomerModel,
    now: datetime,
) -> ConversationSummary:
    return ConversationSummary(
        id=conversation.id,
        channel_type=ChannelType(channel.channel_type),
        status=ConversationStatus(conversation.status),
        priority=ConversationPriority(conversation.priority),
        customer=_customer_summary(customer),
        assignee_user_id=conversation.assignee_user_id,
        last_message_preview=conversation.last_message_preview,
        unread_count=conversation.unread_count,
        tags=list(conversation.tags_json),
        sla_overdue=_sla_overdue(conversation, now),
        last_inbound_at=conversation.last_inbound_at,
        last_outbound_at=conversation.last_outbound_at,
        updated_at=conversation.updated_at,
    )


class InboxRepository:
    def __init__(self, session: Session):
        self._session = session

    def get_conversation_row(self, store_id: str, conversation_id: int) -> ConversationModel:
        conversation = self._session.scalar(
            select(ConversationModel).where(
                ConversationModel.store_id == store_id,
                ConversationModel.id == conversation_id,
            )
        )
        if conversation is None:
            raise NotFoundError(details={"entity": "conversation", "id": conversation_id})
        return conversation

    def list_conversations(
        self,
        store_id: str,
        *,
        status: ConversationStatus | None = None,
        channel_type: ChannelType | None = None,
        assignee_user_id: str | None = None,
        overdue_only: bool = False,
        query: str = "",
        limit: int = 100,
    ) -> list[ConversationSummary]:
        statement = (
            select(ConversationModel, ChannelModel, CustomerModel)
            .join(ChannelModel, ConversationModel.channel_id == ChannelModel.id)
            .join(CustomerModel, ConversationModel.customer_id == CustomerModel.id)
            .where(ConversationModel.store_id == store_id)
            .order_by(ConversationModel.updated_at.desc())
            .limit(limit)
        )
        if status is not None:
            statement = statement.where(ConversationModel.status == status.value)
        if channel_type is not None:
            statement = statement.where(ChannelModel.channel_type == channel_type.value)
        if assignee_user_id is not None:
            statement = statement.where(ConversationModel.assignee_user_id == assignee_user_id)
        if query:
            like = f"%{query}%"
            statement = statement.where(
                ConversationModel.last_message_preview.ilike(like)
                | CustomerModel.display_name.ilike(like)
            )
        now = datetime.now(UTC)
        rows = self._session.execute(statement).all()
        summaries = [
            _summary(conversation, channel, customer, now)
            for conversation, channel, customer in rows
        ]
        if overdue_only:
            summaries = [item for item in summaries if item.sla_overdue]
        return summaries

    def conversation_detail(
        self, store_id: str, conversation_id: int, *, mark_read: bool = False
    ) -> ConversationDetail:
        conversation = self.get_conversation_row(store_id, conversation_id)
        channel = self._session.get(ChannelModel, conversation.channel_id)
        customer = self._session.get(CustomerModel, conversation.customer_id)
        if channel is None or customer is None:
            raise NotFoundError(details={"entity": "conversation", "id": conversation_id})
        if mark_read and conversation.unread_count:
            conversation.unread_count = 0
            self._session.flush()
        messages = self._session.scalars(
            select(MessageModel)
            .where(MessageModel.conversation_id == conversation.id)
            .order_by(MessageModel.created_at, MessageModel.id)
        ).all()
        now = datetime.now(UTC)
        summary = _summary(conversation, channel, customer, now)
        return ConversationDetail(
            **summary.model_dump(),
            messages=[
                MessageOut(
                    id=message.id,
                    direction=MessageDirection(message.direction),
                    sender_type=MessageSenderType(message.sender_type),
                    body=message.body,
                    status=MessageStatus(message.status),
                    external_id=message.external_id,
                    error_message=message.error_message,
                    created_at=message.created_at,
                )
                for message in messages
            ],
        )

    def latest_inbound_text(self, conversation_id: int) -> str | None:
        message = self._session.scalars(
            select(MessageModel)
            .where(
                MessageModel.conversation_id == conversation_id,
                MessageModel.direction == MessageDirection.INBOUND.value,
            )
            .order_by(MessageModel.created_at.desc(), MessageModel.id.desc())
            .limit(1)
        ).first()
        return message.body if message is not None else None
