"""Add durable Stripe billing events and order payment transactions."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260728_0024"
down_revision: str | None = "20260728_0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "subscriptions",
        sa.Column("trial_end", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "subscriptions",
        sa.Column("last_provider_event_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "stripe_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("scope", sa.String(30), nullable=False),
        sa.Column("event_id", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("livemode", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("account_id", sa.String(255), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("scope", "event_id", name="uq_stripe_event_scope_id"),
    )
    op.create_index("ix_stripe_events_scope", "stripe_events", ["scope"])
    op.create_index("ix_stripe_events_event_type", "stripe_events", ["event_type"])

    op.create_table(
        "payment_transactions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("store_id", sa.String(64), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("checkout_session_id", sa.String(255), nullable=True),
        sa.Column("checkout_url", sa.Text(), nullable=True),
        sa.Column("payment_intent_id", sa.String(255), nullable=True),
        sa.Column("amount_numeric", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "refunded_amount_numeric",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_provider_event_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("checkout_session_id", name="uq_payment_checkout_session"),
    )
    for column in (
        "store_id",
        "order_id",
        "provider",
        "status",
        "checkout_session_id",
        "payment_intent_id",
    ):
        op.create_index(
            f"ix_payment_transactions_{column}",
            "payment_transactions",
            [column],
        )


def downgrade() -> None:
    op.drop_table("payment_transactions")
    op.drop_table("stripe_events")
    op.drop_column("subscriptions", "last_provider_event_at")
    op.drop_column("subscriptions", "trial_end")
    op.drop_column("subscriptions", "cancel_at_period_end")
