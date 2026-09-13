"""Revenue opportunities and approval/execution actions."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260727_0010"
down_revision: str | None = "20260727_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "opportunities",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("store_id", sa.String(64), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=True),
        sa.Column("opportunity_type", sa.String(60), nullable=False),
        sa.Column("dedup_key", sa.String(180), nullable=False),
        sa.Column("related_product_ids_json", sa.JSON(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("expected_revenue_numeric", sa.Numeric(12, 2), nullable=False),
        sa.Column("realized_revenue_numeric", sa.Numeric(12, 2), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("suggested_action", sa.Text(), nullable=False),
        sa.Column("channel", sa.String(30), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("execute_after", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("store_id", "dedup_key", name="uq_opportunity_store_dedup"),
    )
    op.create_index("ix_opportunities_store_id", "opportunities", ["store_id"])
    op.create_index("ix_opportunities_customer_id", "opportunities", ["customer_id"])
    op.create_index("ix_opportunities_opportunity_type", "opportunities", ["opportunity_type"])
    op.create_index("ix_opportunities_status", "opportunities", ["status"])

    op.create_table(
        "opportunity_actions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "opportunity_id",
            sa.Integer(),
            sa.ForeignKey("opportunities.id"),
            nullable=False,
        ),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("actor_user_id", sa.String(64), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_opportunity_actions_opportunity_id",
        "opportunity_actions",
        ["opportunity_id"],
    )


def downgrade() -> None:
    op.drop_table("opportunity_actions")
    op.drop_table("opportunities")
