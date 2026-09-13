"""Add provider webhook dedup, consent history, and template reconciliation."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260728_0021"
down_revision: str | None = "20260728_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("channel_templates") as batch:
        batch.add_column(sa.Column("external_id", sa.String(160), nullable=True))
        batch.add_column(
            sa.Column("category", sa.String(30), nullable=False, server_default="UTILITY")
        )
        batch.add_column(sa.Column("rejection_reason", sa.Text(), nullable=True))
        batch.add_column(sa.Column("quality_score", sa.String(30), nullable=True))
        batch.add_column(sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_index("ix_channel_templates_external_id", ["external_id"])

    op.create_table(
        "customer_consents",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("store_id", sa.String(64), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("channel_type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("source", sa.String(60), nullable=False),
        sa.Column("consent_text", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_customer_consents_store_id", "customer_consents", ["store_id"])
    op.create_index(
        "ix_customer_consents_customer_id", "customer_consents", ["customer_id"]
    )
    op.create_index(
        "ix_customer_consents_channel_type", "customer_consents", ["channel_type"]
    )
    op.create_index("ix_customer_consents_status", "customer_consents", ["status"])

    op.create_table(
        "provider_webhook_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("store_id", sa.String(64), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("external_account_id", sa.String(255), nullable=False),
        sa.Column("external_event_id", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "provider",
            "external_account_id",
            "external_event_id",
            name="uq_provider_webhook_event",
        ),
    )
    op.create_index(
        "ix_provider_webhook_events_store_id", "provider_webhook_events", ["store_id"]
    )
    op.create_index(
        "ix_provider_webhook_events_provider", "provider_webhook_events", ["provider"]
    )
    op.create_index(
        "ix_provider_webhook_events_external_account_id",
        "provider_webhook_events",
        ["external_account_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_provider_webhook_events_external_account_id",
        table_name="provider_webhook_events",
    )
    op.drop_index("ix_provider_webhook_events_provider", table_name="provider_webhook_events")
    op.drop_index("ix_provider_webhook_events_store_id", table_name="provider_webhook_events")
    op.drop_table("provider_webhook_events")
    op.drop_index("ix_customer_consents_status", table_name="customer_consents")
    op.drop_index("ix_customer_consents_channel_type", table_name="customer_consents")
    op.drop_index("ix_customer_consents_customer_id", table_name="customer_consents")
    op.drop_index("ix_customer_consents_store_id", table_name="customer_consents")
    op.drop_table("customer_consents")
    with op.batch_alter_table("channel_templates") as batch:
        batch.drop_index("ix_channel_templates_external_id")
        batch.drop_column("last_synced_at")
        batch.drop_column("quality_score")
        batch.drop_column("rejection_reason")
        batch.drop_column("category")
        batch.drop_column("external_id")
