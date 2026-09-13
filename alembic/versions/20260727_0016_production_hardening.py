"""Production hardening: shared limits, inventory reservation, and hot-path indexes."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260727_0016"
down_revision: str | None = "20260727_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("orders") as batch:
        batch.add_column(
            sa.Column("inventory_reserved", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch.create_index("ix_orders_store_status_updated", ["store_id", "status", "updated_at"])
    op.create_table(
        "rate_limit_buckets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("key_hash", sa.String(64), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("key_hash", "window_start", name="uq_rate_limit_key_window"),
    )
    op.create_index("ix_rate_limit_buckets_key_hash", "rate_limit_buckets", ["key_hash"])
    op.create_index("ix_rate_limit_buckets_window_start", "rate_limit_buckets", ["window_start"])
    op.create_index("ix_rate_limit_buckets_expires_at", "rate_limit_buckets", ["expires_at"])
    op.create_index(
        "ix_jobs_status_run_at", "background_jobs", ["status", "run_at", "id"]
    )
    op.create_index(
        "ix_conversations_store_status_updated",
        "conversations",
        ["store_id", "status", "updated_at"],
    )
    op.create_index(
        "ix_messages_conversation_created",
        "messages",
        ["conversation_id", "created_at", "id"],
    )
    op.create_index(
        "ix_events_store_type_created",
        "events",
        ["store_id", "event_type", "created_at"],
    )
    op.create_index(
        "ix_opportunities_store_status_created",
        "opportunities",
        ["store_id", "status", "detected_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_opportunities_store_status_created", table_name="opportunities")
    op.drop_index("ix_events_store_type_created", table_name="events")
    op.drop_index("ix_messages_conversation_created", table_name="messages")
    op.drop_index("ix_conversations_store_status_updated", table_name="conversations")
    op.drop_index("ix_jobs_status_run_at", table_name="background_jobs")
    op.drop_index("ix_rate_limit_buckets_expires_at", table_name="rate_limit_buckets")
    op.drop_index("ix_rate_limit_buckets_window_start", table_name="rate_limit_buckets")
    op.drop_index("ix_rate_limit_buckets_key_hash", table_name="rate_limit_buckets")
    op.drop_table("rate_limit_buckets")
    with op.batch_alter_table("orders") as batch:
        batch.drop_index("ix_orders_store_status_updated")
        batch.drop_column("inventory_reserved")
