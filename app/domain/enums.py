"""Stable domain enumerations."""

from __future__ import annotations

from enum import StrEnum


class MemberRole(StrEnum):
    """Ordered tenant roles; higher value = more privileges."""

    ANALYST = "analyst"
    AGENT = "agent"
    MARKETER = "marketer"
    ADMIN = "admin"
    OWNER = "owner"

    @property
    def rank(self) -> int:
        return _ROLE_RANKS[self]

    def at_least(self, minimum: MemberRole) -> bool:
        return self.rank >= minimum.rank


_ROLE_RANKS: dict[MemberRole, int] = {
    MemberRole.ANALYST: 1,
    MemberRole.AGENT: 2,
    MemberRole.MARKETER: 3,
    MemberRole.ADMIN: 4,
    MemberRole.OWNER: 5,
}


class ProductStatus(StrEnum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    ACTIVE = "active"


class MarketingStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    PUBLISHED = "published"
    PARTIAL = "partial"
    FAILED = "failed"


class PublicationStatus(StrEnum):
    PENDING = "pending"
    DEMO = "demo"
    PUBLISHED = "published"
    DISABLED = "disabled"
    FAILED = "failed"


class Platform(StrEnum):
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"


class CustomerIntent(StrEnum):
    PRODUCT_SEARCH = "product_search"
    PRODUCT_QUESTION = "product_question"
    PRODUCT_COMPARISON = "product_comparison"
    POLICY_QUESTION = "policy_question"
    UNSUPPORTED = "unsupported"


class Language(StrEnum):
    ARABIC = "ar"
    ENGLISH = "en"


class ChannelType(StrEnum):
    WEBCHAT = "webchat"
    WHATSAPP = "whatsapp"
    INSTAGRAM_DM = "instagram_dm"
    MESSENGER = "messenger"
    FACEBOOK_COMMENTS = "facebook_comments"
    INSTAGRAM_COMMENTS = "instagram_comments"


class ChannelMode(StrEnum):
    DEMO = "demo"
    LIVE = "live"


class ProviderConnectionStatus(StrEnum):
    PENDING = "pending"
    CONNECTED = "connected"
    DEGRADED = "degraded"
    EXPIRED = "expired"
    ACTION_REQUIRED = "action_required"
    DISCONNECTED = "disconnected"


class ProviderCapability(StrEnum):
    MESSAGING = "messaging"
    COMMENTS = "comments"
    PUBLISHING = "publishing"
    TEMPLATES = "templates"
    CATALOG_SYNC = "catalog_sync"
    ORDER_SYNC = "order_sync"


class ConversationStatus(StrEnum):
    OPEN = "open"
    PENDING = "pending"
    RESOLVED = "resolved"
    SNOOZED = "snoozed"


class ConversationPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class MessageDirection(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class MessageSenderType(StrEnum):
    CUSTOMER = "customer"
    AGENT = "agent"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    NOTE = "note"


class MessageStatus(StrEnum):
    RECEIVED = "received"
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    DELIVERY_UNKNOWN = "delivery_unknown"


class EventType(StrEnum):
    PAGE_VIEW = "page_view"
    PRODUCT_VIEW = "product_view"
    SEARCH = "search"
    ADD_TO_CART = "add_to_cart"
    CHECKOUT_STARTED = "checkout_started"
    PURCHASE = "purchase"
    CONTENT_ENGAGEMENT = "content_engagement"
    CONTENT_CLICK = "content_click"


class OrderStatus(StrEnum):
    DRAFT = "draft"
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PAID = "paid"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class OpportunityStatus(StrEnum):
    NEW = "new"
    AWAITING_APPROVAL = "awaiting_approval"
    EXECUTED = "executed"
    WON = "won"
    REJECTED = "rejected"


class AutomationTrigger(StrEnum):
    NEW_MESSAGE = "new_message"
    NEW_COMMENT = "new_comment"
    LEAD_SCORE_INCREASED = "lead_score_increased"
    ABANDONED_CART = "abandoned_cart"
    ORDER_STATUS_CHANGED = "order_status_changed"
    CUSTOMER_INACTIVE = "customer_inactive"
    LOW_STOCK = "low_stock"
    NEW_OPPORTUNITY = "new_opportunity"
    SCHEDULED = "scheduled"


class AutomationActionType(StrEnum):
    DRAFT_REPLY = "draft_reply"
    SEND_MESSAGE = "send_message"
    CREATE_OPPORTUNITY = "create_opportunity"
    ADD_TAG = "add_tag"
    ASSIGN_TEAMMATE = "assign_teammate"
    CREATE_DRAFT_ORDER = "create_draft_order"
    RAISE_ALERT = "raise_alert"
    GENERATE_CONTENT = "generate_content"
    REQUEST_APPROVAL = "request_approval"
