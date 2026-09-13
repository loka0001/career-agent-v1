"""Unified inbox endpoints: list, detail, reply, suggest, manage, simulate."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Header, status

from app.api.dependencies import (
    AgentUser,
    ContainerDependency,
    CurrentUser,
    DatabaseDependency,
)
from app.api.routes.sales import build_assist_use_case
from app.api.schemas import ConversationListResponse, MessageResponse
from app.domain.enums import ChannelMode, ChannelType, ConversationStatus, MessageSenderType
from app.domain.errors import ConflictError
from app.domain.models import (
    ConversationDetail,
    ConversationUpdateInput,
    MessageOut,
    NoteInput,
    ReplyInput,
    SalesAssistantResponse,
    SimulateInboundInput,
)
from app.repositories.inbox_repository import InboxRepository
from app.services.conversations import (
    add_internal_note,
    ensure_channel,
    ingest_inbound_message,
    queue_outbound_message,
)

router = APIRouter(prefix="/inbox", tags=["inbox"])


@router.get("/conversations", response_model=ConversationListResponse)
def list_conversations(
    user: CurrentUser,
    container: ContainerDependency,
    db: DatabaseDependency,
    status_filter: ConversationStatus | None = None,
    channel: ChannelType | None = None,
    assignee: str | None = None,
    overdue: bool = False,
    q: str = "",
) -> ConversationListResponse:
    conversations = InboxRepository(db).list_conversations(
        user.store_id,
        status=status_filter,
        channel_type=channel,
        assignee_user_id=assignee,
        overdue_only=overdue,
        query=q,
    )
    return ConversationListResponse(
        conversations=conversations,
        demo_available=container.settings.demo_mode,
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def conversation_detail(
    conversation_id: int, user: CurrentUser, db: DatabaseDependency
) -> ConversationDetail:
    return InboxRepository(db).conversation_detail(
        user.store_id, conversation_id, mark_read=True
    )


@router.post(
    "/conversations/{conversation_id}/reply",
    response_model=MessageOut,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Queue an agent reply for delivery through the conversation channel",
)
def reply(
    conversation_id: int,
    payload: ReplyInput,
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=8, max_length=128),
    ],
    user: AgentUser,
    db: DatabaseDependency,
) -> MessageOut:
    repository = InboxRepository(db)
    conversation = repository.get_conversation_row(user.store_id, conversation_id)
    message = queue_outbound_message(
        db,
        store_id=user.store_id,
        conversation=conversation,
        text=payload.text,
        sender_type=MessageSenderType.AGENT,
        sender_user_id=user.user_id,
        idempotency_key=idempotency_key,
        audit_actor=user.email,
        audit_organization_id=user.organization_id,
    )
    return MessageOut.model_validate(message, from_attributes=True)


@router.post(
    "/conversations/{conversation_id}/suggest",
    response_model=SalesAssistantResponse,
    summary="Grounded AI suggestion for the latest customer message",
)
def suggest(
    conversation_id: int,
    user: AgentUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> SalesAssistantResponse:
    repository = InboxRepository(db)
    repository.get_conversation_row(user.store_id, conversation_id)
    latest = repository.latest_inbound_text(conversation_id)
    if latest is None:
        raise ConflictError("Conversation has no customer message yet")
    return build_assist_use_case(container, db).execute(user.store_id, latest)


@router.patch("/conversations/{conversation_id}", response_model=ConversationDetail)
def update_conversation(
    conversation_id: int,
    payload: ConversationUpdateInput,
    user: AgentUser,
    db: DatabaseDependency,
) -> ConversationDetail:
    repository = InboxRepository(db)
    conversation = repository.get_conversation_row(user.store_id, conversation_id)
    if payload.status is not None:
        conversation.status = payload.status.value
        if payload.status != ConversationStatus.OPEN:
            conversation.sla_due_at = None
    if payload.priority is not None:
        conversation.priority = payload.priority.value
    if payload.assignee_user_id is not None:
        conversation.assignee_user_id = payload.assignee_user_id or None
    if payload.tags is not None:
        conversation.tags_json = payload.tags
    db.flush()
    return repository.conversation_detail(user.store_id, conversation_id)


@router.post("/conversations/{conversation_id}/notes", response_model=MessageOut)
def add_note(
    conversation_id: int,
    payload: NoteInput,
    user: AgentUser,
    db: DatabaseDependency,
) -> MessageOut:
    conversation = InboxRepository(db).get_conversation_row(user.store_id, conversation_id)
    note = add_internal_note(
        db, conversation=conversation, text=payload.text, sender_user_id=user.user_id
    )
    return MessageOut.model_validate(note, from_attributes=True)


@router.post(
    "/simulate",
    response_model=ConversationDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Demo mode: inject an inbound customer message",
)
def simulate_inbound(
    payload: SimulateInboundInput,
    user: AgentUser,
    container: ContainerDependency,
    db: DatabaseDependency,
) -> ConversationDetail:
    if not container.settings.demo_mode:
        raise ConflictError("Inbound simulation is disabled outside demo mode")
    channel = ensure_channel(db, user.store_id, payload.channel_type)
    if channel.mode != ChannelMode.DEMO.value:
        raise ConflictError(
            "Simulation is only available for demo-mode channels",
            details={"channel": payload.channel_type.value},
        )
    conversation, _ = ingest_inbound_message(
        db,
        store_id=user.store_id,
        channel_type=payload.channel_type,
        external_user_id=payload.external_id or f"demo-{uuid.uuid4().hex[:8]}",
        text=payload.text,
        display_name=payload.customer_name,
    )
    return InboxRepository(db).conversation_detail(user.store_id, conversation.id)


@router.post("/mark-all-read", response_model=MessageResponse)
def mark_all_read(user: AgentUser, db: DatabaseDependency) -> MessageResponse:
    for summary in InboxRepository(db).list_conversations(user.store_id):
        if summary.unread_count:
            row = InboxRepository(db).get_conversation_row(user.store_id, summary.id)
            row.unread_count = 0
    db.flush()
    return MessageResponse(message="all_read")
