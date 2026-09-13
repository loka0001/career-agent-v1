"""Plans, subscriptions, and monthly usage counters."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260727_0014"
down_revision: str | None = "20260727_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "plans",
        sa.Column("key", sa.String(30), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("price_numeric", sa.Numeric(12, 2), nullable=False),
        sa.Column("quotas_json", sa.JSON(), nullable=False),
        sa.Column("features_json", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "organization_id",
            sa.String(64),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("plan_key", sa.String(30), sa.ForeignKey("plans.key"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("provider_customer_id", sa.String(160), nullable=True),
        sa.Column("provider_subscription_id", sa.String(160), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id"),
    )
    op.create_index("ix_subscriptions_organization_id", "subscriptions", ["organization_id"])
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"])
    op.create_table(
        "usage_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "organization_id",
            sa.String(64),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("store_id", sa.String(64), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("metric", sa.String(50), nullable=False),
        sa.Column("period_key", sa.String(7), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "organization_id",
            "store_id",
            "metric",
            "period_key",
            name="uq_usage_period_metric",
        ),
    )
    op.create_index("ix_usage_records_organization_id", "usage_records", ["organization_id"])
    op.create_index("ix_usage_records_store_id", "usage_records", ["store_id"])
    op.create_index("ix_usage_records_metric", "usage_records", ["metric"])


def downgrade() -> None:
    op.drop_table("usage_records")
    op.drop_table("subscriptions")
    op.drop_table("plans")
