"""Add per-store AI budget and measured invocation metadata."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260729_0027"
down_revision: str | None = "20260729_0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "store_settings",
        sa.Column(
            "ai_monthly_budget_numeric",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="25.00",
        ),
    )
    op.add_column("ai_usage_records", sa.Column("latency_ms", sa.Integer(), nullable=True))
    op.add_column(
        "ai_usage_records",
        sa.Column(
            "cost_source",
            sa.String(20),
            nullable=False,
            server_default="unknown",
        ),
    )


def downgrade() -> None:
    op.drop_column("ai_usage_records", "cost_source")
    op.drop_column("ai_usage_records", "latency_ms")
    op.drop_column("store_settings", "ai_monthly_budget_numeric")
