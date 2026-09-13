"""Omnichannel core: channels, customers, identities, conversations, messages."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260727_0004"
down_revision: str | None = "20260727_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "channels",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("store_id", sa.String(64), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("channel_type", sa.String(30), nullable=False),
        sa.Column("mode", sa.String(10), nullable=False),
        sa.Column("display_name", sa.String(160), nullable=False),
        sa.Column("credentials_json", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("store_id", "channel_type", name="uq_channel_store_type"),
    )
    op.create_index("ix_channels_store_id", "channels", ["store_id"])
    op.create_index("ix_channels_channel_type", "channels", ["channel_type"])

    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("store_id", sa.String(64), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("display_name", sa.String(160), nullable=False),
        sa.Column("phone", sa.String(40), nullable=True),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("tags_json", sa.JSON(), nullable=False),
        sa.Column("consent_json", sa.JSON(), nullable=False),
        sa.Column("attributes_json", sa.JSON(), nullable=False),
        sa.Column("lead_score", sa.Integer(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_customers_store_id", "customers", ["store_id"])
    op.create_index("ix_customers_phone", "customers", ["phone"])
    op.create_index("ix_customers_email", "customers", ["email"])

    op.create_table(
        "customer_identities",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("store_id", sa.String(64), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("channel_type", sa.String(30), nullable=False),
        sa.Column("external_id", sa.String(160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "store_id", "channel_type", "external_id", name="uq_identity_store_channel_ext"
        ),
    )
    op.create_index("ix_customer_identities_store_id", "customer_identities", ["store_id"])
    op.create_index("ix_customer_identities_customer_id", "customer_identities", ["customer_id"])

    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("store_id", sa.String(64), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("channel_id", sa.Integer(), sa.ForeignKey("channels.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("priority", sa.String(10), nullable=False),
        sa.Column("assignee_user_id", sa.String(64), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("last_message_preview", sa.String(300), nullable=False),
        sa.Column("unread_count", sa.Integer(), nullable=False),
        sa.Column("tags_json", sa.JSON(), nullable=False),
        sa.Column("last_inbound_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_outbound_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sla_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_conversations_store_id", "conversations", ["store_id"])
    op.create_index("ix_conversations_customer_id", "conversations", ["customer_id"])
    op.create_index("ix_conversations_channel_id", "conversations", ["channel_id"])
    op.create_index("ix_conversations_status", "conversations", ["status"])
    op.create_index("ix_conversations_priority", "conversations", ["priority"])
    op.create_index("ix_conversations_assignee_user_id", "conversations", ["assignee_user_id"])
    op.create_index("ix_conversations_updated_at", "conversations", ["updated_at"])

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "conversation_id", sa.Integer(), sa.ForeignKey("conversations.id"), nullable=False
        ),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("sender_type", sa.String(15), nullable=False),
        sa.Column("sender_user_id", sa.String(64), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("attachments_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(15), nullable=False),
        sa.Column("external_id", sa.String(160), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index("ix_messages_status", "messages", ["status"])
    op.create_index("ix_messages_created_at", "messages", ["created_at"])


def downgrade() -> None:
    for table in ("messages", "conversations", "customer_identities", "customers", "channels"):
        op.drop_table(table)
