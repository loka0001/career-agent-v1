"""Automation definitions and idempotent run history."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260727_0011"
down_revision: str | None = "20260727_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "automations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("store_id", sa.String(64), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("trigger_type", sa.String(50), nullable=False),
        sa.Column("conditions_json", sa.JSON(), nullable=False),
        sa.Column("actions_json", sa.JSON(), nullable=False),
        sa.Column("delay_seconds", sa.Integer(), nullable=False),
        sa.Column("approval_required", sa.Boolean(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("template_key", sa.String(80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_automations_store_id", "automations", ["store_id"])
    op.create_index("ix_automations_trigger_type", "automations", ["trigger_type"])
    op.create_index("ix_automations_is_enabled", "automations", ["is_enabled"])

    op.create_table(
        "automation_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "automation_id",
            sa.Integer(),
            sa.ForeignKey("automations.id"),
            nullable=False,
        ),
        sa.Column("store_id", sa.String(64), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("event_key", sa.String(180), nullable=False),
        sa.Column("event_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("automation_id", "event_key", name="uq_automation_run_event"),
    )
    op.create_index("ix_automation_runs_automation_id", "automation_runs", ["automation_id"])
    op.create_index("ix_automation_runs_store_id", "automation_runs", ["store_id"])
    op.create_index("ix_automation_runs_status", "automation_runs", ["status"])


def downgrade() -> None:
    op.drop_table("automation_runs")
    op.drop_table("automations")
