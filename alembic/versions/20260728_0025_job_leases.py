"""Add durable leases and heartbeats to background jobs."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260728_0025"
down_revision: str | None = "20260728_0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("background_jobs", sa.Column("lease_token", sa.String(64), nullable=True))
    op.add_column(
        "background_jobs",
        sa.Column("leased_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "background_jobs",
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "background_jobs",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_background_jobs_lease_token",
        "background_jobs",
        ["lease_token"],
    )
    op.create_index(
        "ix_background_jobs_leased_until",
        "background_jobs",
        ["leased_until"],
    )


def downgrade() -> None:
    op.drop_index("ix_background_jobs_leased_until", table_name="background_jobs")
    op.drop_index("ix_background_jobs_lease_token", table_name="background_jobs")
    op.drop_column("background_jobs", "started_at")
    op.drop_column("background_jobs", "heartbeat_at")
    op.drop_column("background_jobs", "leased_until")
    op.drop_column("background_jobs", "lease_token")
