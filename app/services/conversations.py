"""Conversation lifecycle: inbound ingestion, outbound sending via jobs, SLA."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import (
    ChannelModel,
    ChannelTemplateModel,
    ConversationModel,
    CustomerIdentityModel,
    CustomerModel,
    MessageModel,
    StoreModel,
)
from app.domain.enums import (
    ChannelMode,
    ChannelType,
    ConversationStatus,
    MessageDirection,
    MessageSenderType,
    MessageStatus,
)
from app.domain.errors import ConflictError, NotFoundError
from app.integrations.channels import resolve_adapter
from app.repositories.audit_repository import AuditRepository
from app.repositories.provider_connection_repository import ProviderConnectionRepository
from app.services.billing import (
    channel_family,
    check_and_increment,
    check_resource_limit,
    organization_channel_count,
)
from app.services.credential_vault import decrypt_configured_credentials
from app.services.external_operations import (
    begin_external_operation,
    complete_external_operation,
    mark_external_operation_retryable,
    mark_external_operation_unknown,
)
from app.services.job_queue import enqueue_job, job_handler

DEFAULT_SLA_MINUTES = 15
PREVIEW_LENGTH = 140
WHATSAPP_SERVICE_WINDOW = timedelta(hours=24)


def utc_now() -> datetime:
    return datetime.now(UTC)


def _preview(text: str) -> str:
    cleaned = " ".join(text.split())
    return cleaned[:PREVIEW_LENGTH]


def ensure_channel(
    session: Session,
    store_id: str,
    channel_type: ChannelType,
    *,
    mode: ChannelMode = ChannelMode.DEMO,
    display_name: str = "",
) -> ChannelModel:
    channel = session.scalar(
        select(ChannelModel).where(
            ChannelModel.store_id == store_id,
            ChannelModel.channel_type == channel_type.value,
        )
    )
    if channel is None:
        store = session.get(StoreModel, store_id)
        organization_id = store.organization_id if store is not None else None
        family_exists = session.scalar(
            select(ChannelModel.id)
            .join(StoreModel, StoreModel.id == ChannelModel.store_id)
            .where(
                StoreModel.organization_id == organization_id,
                ChannelModel.channel_type.in_(
                    {
                        candidate.value
                        for candidate in ChannelType
                        if channel_family(candidate.value) == channel_family(channel_type.value)
                    }
                ),
            )
        )
        if family_exists is None:
            check_resource_limit(
                session,
                store_id,
                "channels",
                organization_channel_count(session, organization_id),
            )
        try:
            with session.begin_nested():
                channel = ChannelModel(
                    store_id=store_id,
                    channel_type=channel_type.value,
                    mode=mode.value,
                    display_name=display_name or channel_type.value,
                )
                session.add(channel)
                session.flush()
        except IntegrityError:
            channel = session.scalar(
                select(ChannelModel).where(
                    ChannelModel.store_id == store_id,
                    ChannelModel.channel_type == channel_type.value,
                )
            )
            if channel is None:
                raise
    return channel


def resolve_customer(
    session: Session,
    store_id: str,
    channel_type: ChannelType,
    external_id: str,
    *,
    display_name: str = "",
    phone: str | None = None,
    email: str | None = None,
) -> CustomerModel:
    """Find the customer behind a channel identity, unifying by phone/email."""

    identity = session.scalar(
        select(CustomerIdentityModel).where(
            CustomerIdentityModel.store_id == store_id,
            CustomerIdentityModel.channel_type == channel_type.value,
            CustomerIdentityModel.external_id == external_id,
        )
    )
    if identity is not None:
        customer = session.get(CustomerModel, identity.customer_id)
        if customer is None:
            raise NotFoundError(details={"entity": "customer", "id": identity.customer_id})
        customer.last_seen_at = utc_now()
        if display_name and not customer.display_name:
            customer.display_name = display_name
        session.flush()
        return customer

    customer = None
    if phone:
        customer = session.scalar(
            select(CustomerModel).where(
                CustomerModel.store_id == store_id, CustomerModel.phone == phone
            )
        )
    if customer is None and email:
        customer = session.scalar(
            select(CustomerModel).where(
                CustomerModel.store_id == store_id, CustomerModel.email == email
            )
        )
    if customer is None:
        customer = CustomerModel(
            store_id=store_id,
            display_name=display_name or "عميل",
            phone=phone,
            email=email,
            consent_json={},
        )
        session.add(customer)
        session.flush()
    else:
        customer.last_seen_at = utc_now()
    session.add(
        CustomerIdentityModel(
            store_id=store_id,
            customer_id=customer.id,
            channel_type=channel_type.value,
            external_id=external_id,
        )
    )
    session.flush()
    return customer


def ingest_inbound_message(
    session: Session,
    *,
    store_id: str,
    channel_type: ChannelType,
    external_user_id: str,
    text: str,
    display_name: str = "",
    phone: str | None = None,
    email: str | None = None,
    external_message_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    sla_minutes: int = DEFAULT_SLA_MINUTES,
) -> tuple[ConversationModel, MessageModel]:
    """Store an inbound message, creating channel/customer/conversation as needed.

    Idempotent per (conversation, external_message_id): webhook retries are safe.
    """

    channel = ensure_channel(session, store_id, channel_type)
    customer = resolve_customer(
        session,
        store_id,
        channel_type,
        external_user_id,
        display_name=display_name,
        phone=phone,
        email=email,
    )
    conversation = session.scalar(
        select(ConversationModel)
        .where(
            ConversationModel.store_id == store_id,
            ConversationModel.customer_id == customer.id,
            ConversationModel.channel_id == channel.id,
            ConversationModel.status != ConversationStatus.RESOLVED.value,
        )
        .order_by(ConversationModel.id.desc())
    )
    if conversation is None:
        check_and_increment(session, store_id, "conversations")
        conversation = ConversationModel(
            store_id=store_id, customer_id=customer.id, channel_id=channel.id
        )
        session.add(conversation)
        session.flush()

    if external_message_id is not None:
        duplicate = session.scalar(
            select(MessageModel).where(
                MessageModel.conversation_id == conversation.id,
                MessageModel.external_id == external_message_id,
            )
        )
        if duplicate is not None:
            return conversation, duplicate

    def persist_message() -> MessageModel:
        now = utc_now()
        inbound = MessageModel(
            conversation_id=conversation.id,
            direction=MessageDirection.INBOUND.value,
            sender_type=MessageSenderType.CUSTOMER.value,
            body=text,
            status=MessageStatus.RECEIVED.value,
            external_id=external_message_id,
            metadata_json=metadata or {},
        )
        session.add(inbound)
        conversation.last_message_preview = _preview(text)
        conversation.unread_count += 1
        conversation.last_inbound_at = now
        conversation.status = ConversationStatus.OPEN.value
        conversation.sla_due_at = now + timedelta(minutes=sla_minutes)
        session.flush()
        return inbound

    if external_message_id is None:
        message = persist_message()
    else:
        try:
            with session.begin_nested():
                message = persist_message()
        except IntegrityError:
            duplicate = session.scalar(
                select(MessageModel).where(
                    MessageModel.conversation_id == conversation.id,
                    MessageModel.external_id == external_message_id,
                )
            )
            if duplicate is None:
                raise
            return conversation, duplicate
    from app.domain.enums import AutomationTrigger
    from app.services.automations import dispatch_automation_event

    trigger = (
        AutomationTrigger.NEW_COMMENT
        if channel_type in {ChannelType.FACEBOOK_COMMENTS, ChannelType.INSTAGRAM_COMMENTS}
        else AutomationTrigger.NEW_MESSAGE
    )
    dispatch_automation_event(
        session,
        store_id,
        trigger,
        {
            "conversation_id": conversation.id,
            "customer_id": customer.id,
            "message_id": message.id,
            "channel_type": channel_type.value,
            "text": text,
        },
        f"message:{message.id}",
    )
    return conversation, message


def queue_outbound_message(
    session: Session,
    *,
    store_id: str,
    conversation: ConversationModel,
    text: str,
    sender_type: MessageSenderType = MessageSenderType.AGENT,
    sender_user_id: str | None = None,
    template: ChannelTemplateModel | None = None,
    template_variables: dict[str, str] | None = None,
    attachments: list[dict[str, str]] | None = None,
    idempotency_key: str | None = None,
    audit_actor: str | None = None,
    audit_organization_id: str | None = None,
) -> MessageModel:
    """Create a queued outbound message and schedule delivery on the job queue."""

    channel = session.get(ChannelModel, conversation.channel_id)
    if channel is None or not channel.is_active:
        raise ConflictError("Conversation channel is not active")
    customer = session.get(CustomerModel, conversation.customer_id)
    if customer is None:
        raise NotFoundError(details={"entity": "customer"})
    consent = dict(customer.consent_json)
    channel_consent = consent.get(channel.channel_type)
    if channel_consent is False:
        raise ConflictError(
            "Customer has opted out of this channel",
            details={"channel": channel.channel_type},
        )
    if (
        channel.channel_type == ChannelType.WHATSAPP.value
        and template is not None
        and channel_consent is not True
    ):
        raise ConflictError(
            "WhatsApp marketing consent is required for template messages",
            details={"channel": channel.channel_type, "reason": "opt_in_required"},
        )
    if channel.channel_type == ChannelType.WHATSAPP.value and template is None:
        last_inbound = conversation.last_inbound_at
        if last_inbound is None:
            raise ConflictError(
                "A WhatsApp template is required outside the customer service window",
                details={"reason": "service_window_closed"},
            )
        if last_inbound.tzinfo is None:
            last_inbound = last_inbound.replace(tzinfo=UTC)
        if utc_now() - last_inbound > WHATSAPP_SERVICE_WINDOW:
            raise ConflictError(
                "A WhatsApp template is required outside the customer service window",
                details={"reason": "service_window_closed"},
            )
    metadata: dict[str, Any] = {}
    if template is not None:
        if (
            template.store_id != store_id
            or template.channel_id != channel.id
            or template.status != "approved"
        ):
            raise ConflictError("WhatsApp template is not approved for this channel")
        values = template_variables or {}
        missing = [name for name in template.variables_json if name not in values]
        if missing:
            raise ConflictError(
                "WhatsApp template variables are incomplete",
                details={"missing": missing},
            )
        metadata = {
            "template": {
                "name": template.name,
                "language": template.language,
                "parameters": [values[name] for name in template.variables_json],
            }
        }
    attachment_payload = attachments or []
    if idempotency_key is not None:
        existing = session.scalar(
            select(MessageModel).where(
                MessageModel.conversation_id == conversation.id,
                MessageModel.client_request_id == idempotency_key,
            )
        )
        if existing is not None:
            if (
                existing.body != text
                or existing.sender_type != sender_type.value
                or existing.sender_user_id != sender_user_id
                or existing.attachments_json != attachment_payload
                or existing.metadata_json != metadata
            ):
                raise ConflictError(
                    "Idempotency-Key was already used for a different reply",
                    details={"reason": "idempotency_key_reused"},
                )
            return existing

    message = MessageModel(
        conversation_id=conversation.id,
        direction=MessageDirection.OUTBOUND.value,
        sender_type=sender_type.value,
        sender_user_id=sender_user_id,
        body=text,
        attachments_json=attachment_payload,
        status=MessageStatus.QUEUED.value,
        metadata_json=metadata,
        client_request_id=idempotency_key,
    )
    if idempotency_key is None:
        session.add(message)
        session.flush()
    else:
        try:
            with session.begin_nested():
                session.add(message)
                session.flush()
        except IntegrityError as exc:
            existing = session.scalar(
                select(MessageModel).where(
                    MessageModel.conversation_id == conversation.id,
                    MessageModel.client_request_id == idempotency_key,
                )
            )
            if existing is None:
                raise
            if (
                existing.body != text
                or existing.sender_type != sender_type.value
                or existing.sender_user_id != sender_user_id
                or existing.attachments_json != attachment_payload
                or existing.metadata_json != metadata
            ):
                raise ConflictError(
                    "Idempotency-Key was already used for a different reply",
                    details={"reason": "idempotency_key_reused"},
                ) from exc
            return existing
    conversation.last_message_preview = _preview(text)
    conversation.unread_count = 0
    conversation.last_outbound_at = utc_now()
    conversation.sla_due_at = None
    session.flush()
    enqueue_job(
        session,
        job_type="channel.send_message",
        store_id=store_id,
        payload={"message_id": message.id},
        dedup_key=f"send-message-{message.id}",
    )
    if audit_actor is not None:
        AuditRepository(session).add(
            actor=audit_actor,
            action="outbound_message.queued",
            entity_type="message",
            entity_id=str(message.id),
            metadata={
                "conversation_id": conversation.id,
                "channel_type": channel.channel_type,
            },
            organization_id=audit_organization_id,
            store_id=store_id,
            actor_user_id=sender_user_id,
        )
    return message


def add_internal_note(
    session: Session,
    *,
    conversation: ConversationModel,
    text: str,
    sender_user_id: str | None,
) -> MessageModel:
    note = MessageModel(
        conversation_id=conversation.id,
        direction=MessageDirection.OUTBOUND.value,
        sender_type=MessageSenderType.NOTE.value,
        sender_user_id=sender_user_id,
        body=text,
        status=MessageStatus.SENT.value,
    )
    session.add(note)
    session.flush()
    return note


@job_handler("channel.send_message")
def deliver_queued_message(session: Session, payload: dict[str, Any]) -> None:
    """Job handler: deliver one queued outbound message through its channel adapter."""

    message = session.get(MessageModel, int(payload["message_id"]))
    if message is None or message.status not in {
        MessageStatus.QUEUED.value,
        MessageStatus.SENDING.value,
        MessageStatus.FAILED.value,
    }:
        return
    conversation = session.get(ConversationModel, message.conversation_id)
    if conversation is None:
        return
    channel = session.get(ChannelModel, conversation.channel_id)
    customer = session.get(CustomerModel, conversation.customer_id)
    if channel is None or customer is None:
        message.status = MessageStatus.FAILED.value
        message.error_message = "channel_or_customer_missing"
        return
    identity = session.scalar(
        select(CustomerIdentityModel).where(
            CustomerIdentityModel.customer_id == customer.id,
            CustomerIdentityModel.channel_type == channel.channel_type,
        )
    )
    recipient = identity.external_id if identity is not None else str(customer.id)
    adapter = resolve_adapter(ChannelType(channel.channel_type), ChannelMode(channel.mode))
    if channel.provider_connection_id:
        credentials = ProviderConnectionRepository(session, channel.store_id).credentials(
            channel.provider_connection_id
        )
    else:
        credentials = dict(channel.credentials_json)
        if "ciphertext" in credentials:
            credentials = decrypt_configured_credentials(credentials)
    operation_key = f"outbound-message:{message.id}"
    decision = begin_external_operation(
        session,
        store_id=channel.store_id,
        operation_key=operation_key,
        operation_type="channel.send_message",
        entity_type="message",
        entity_id=str(message.id),
    )
    if decision.requires_reconciliation:
        message.status = MessageStatus.DELIVERY_UNKNOWN.value
        message.error_message = "provider_outcome_unknown_manual_review_required"
        message.metadata_json = {
            **message.metadata_json,
            "delivery_attempt_id": decision.attempt_id,
            "delivery_outcome": "unknown",
        }
        store = session.get(StoreModel, channel.store_id)
        AuditRepository(session).add(
            actor="system",
            action="outbound_message.delivery_unknown",
            entity_type="message",
            entity_id=str(message.id),
            metadata={
                "conversation_id": conversation.id,
                "channel_type": channel.channel_type,
                "attempt_id": decision.attempt_id,
                "operation_key": operation_key,
                "manual_review_required": True,
            },
            organization_id=store.organization_id if store is not None else None,
            store_id=channel.store_id,
        )
        return
    if not decision.should_execute:
        message.status = MessageStatus.SENT.value
        message.external_id = decision.external_id
        message.error_message = None
        return
    message.status = MessageStatus.SENDING.value
    message.metadata_json = {
        **message.metadata_json,
        "delivery_attempt_id": decision.attempt_id,
        "delivery_outcome": "in_flight",
    }
    # Persist the operator-visible attempt marker before crossing the network boundary.
    session.commit()
    template_data = message.metadata_json.get("template")
    attachment_data = message.attachments_json[0] if message.attachments_json else None
    if isinstance(attachment_data, dict):
        result = adapter.send_media(
            credentials,
            recipient,
            str(attachment_data.get("type", "")),
            str(attachment_data.get("url", "")),
            message.body,
            (str(attachment_data.get("filename")) if attachment_data.get("filename") else None),
        )
    elif isinstance(template_data, dict):
        result = adapter.send_template(
            credentials,
            recipient,
            str(template_data.get("name", "")),
            str(template_data.get("language", "ar")),
            [str(value) for value in template_data.get("parameters", [])],
        )
    else:
        result = adapter.send_text(credentials, recipient, message.body)
    if result.success:
        complete_external_operation(
            session,
            channel.store_id,
            operation_key,
            external_id=result.external_id,
        )
        message.status = MessageStatus.SENT.value
        message.external_id = result.external_id
        message.error_message = None
        message.metadata_json = {
            **message.metadata_json,
            "delivery_outcome": "succeeded",
        }
        store = session.get(StoreModel, channel.store_id)
        AuditRepository(session).add(
            actor="system",
            action="outbound_message.sent",
            entity_type="message",
            entity_id=str(message.id),
            metadata={
                "conversation_id": conversation.id,
                "channel_type": channel.channel_type,
                "channel_mode": channel.mode,
            },
            organization_id=store.organization_id if store is not None else None,
            store_id=channel.store_id,
        )
    else:
        # Persist the failure before raising: the raise triggers the queue's
        # retry/backoff, and the rollback must not erase the visible status.
        error = f"{result.error_code}: {result.error_message}"
        if result.error_code == "transport_error":
            operation = mark_external_operation_unknown(session, channel.store_id, operation_key)
            message.status = MessageStatus.DELIVERY_UNKNOWN.value
            message.error_message = "provider_outcome_unknown_manual_review_required"
            message.metadata_json = {
                **message.metadata_json,
                "delivery_outcome": "unknown",
            }
            store = session.get(StoreModel, channel.store_id)
            AuditRepository(session).add(
                actor="system",
                action="outbound_message.delivery_unknown",
                entity_type="message",
                entity_id=str(message.id),
                metadata={
                    "conversation_id": conversation.id,
                    "channel_type": channel.channel_type,
                    "attempt_id": operation.attempt_id,
                    "operation_key": operation_key,
                    "manual_review_required": True,
                },
                organization_id=store.organization_id if store is not None else None,
                store_id=channel.store_id,
            )
            return
        mark_external_operation_retryable(
            session,
            channel.store_id,
            operation_key,
            result.error_code,
        )
        message.status = MessageStatus.FAILED.value
        message.error_message = error
        message.metadata_json = {
            **message.metadata_json,
            "delivery_outcome": "retryable_failure",
        }
        store = session.get(StoreModel, channel.store_id)
        AuditRepository(session).add(
            actor="system",
            action="outbound_message.failed",
            entity_type="message",
            entity_id=str(message.id),
            metadata={
                "conversation_id": conversation.id,
                "channel_type": channel.channel_type,
                "channel_mode": channel.mode,
                "error_code": result.error_code,
            },
            organization_id=store.organization_id if store is not None else None,
            store_id=channel.store_id,
        )
        session.commit()
        raise RuntimeError(error)
