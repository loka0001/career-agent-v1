"""Enforce reply idempotency and durable Content Studio approvals."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260831_0029"
down_revision: str | None = "20260729_0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("client_request_id", sa.String(128), nullable=True))
    op.create_index(
        "uq_message_conversation_client_request",
        "messages",
        ["conversation_id", "client_request_id"],
        unique=True,
    )

    op.add_column(
        "content_items", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("content_items", sa.Column("approved_by", sa.String(320), nullable=True))
    op.add_column(
        "content_items",
        sa.Column("approved_by_user_id", sa.String(64), sa.ForeignKey("users.id"), nullable=True),
    )
    op.add_column(
        "content_items", sa.Column("approved_content_hash", sa.String(64), nullable=True)
    )
    op.create_index(
        "ix_content_items_approved_by_user_id",
        "content_items",
        ["approved_by_user_id"],
    )
    # Legacy approval states have no actor, timestamp, or content digest. Force
    # merchant review again instead of treating them as publishable evidence.
    op.execute(
        "UPDATE content_items SET status = 'draft' "
        "WHERE status IN ('approved', 'scheduled')"
    )


def downgrade() -> None:
    op.drop_index("ix_content_items_approved_by_user_id", table_name="content_items")
    op.drop_column("content_items", "approved_content_hash")
    op.drop_column("content_items", "approved_by_user_id")
    op.drop_column("content_items", "approved_by")
    op.drop_column("content_items", "approved_at")

    op.drop_index("uq_message_conversation_client_request", table_name="messages")
    op.drop_column("messages", "client_request_id")
