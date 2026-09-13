"""Add a durable ledger for ambiguous external-provider operations."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260902_0030"
down_revision: str | None = "20260831_0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "external_operations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.String(64), nullable=False),
        sa.Column("operation_key", sa.String(180), nullable=False),
        sa.Column("operation_type", sa.String(80), nullable=False),
        sa.Column("entity_type", sa.String(80), nullable=False),
        sa.Column("entity_id", sa.String(100), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("attempt_id", sa.String(64), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("last_error_code", sa.String(100), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("store_id", "operation_key", name="uq_external_operation_store_key"),
    )
    op.create_index("ix_external_operations_store_id", "external_operations", ["store_id"])
    op.create_index(
        "ix_external_operations_operation_type", "external_operations", ["operation_type"]
    )
    op.create_index("ix_external_operations_status", "external_operations", ["status"])
    op.create_index(
        "ix_external_operations_attempt_id",
        "external_operations",
        ["attempt_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_external_operations_attempt_id", table_name="external_operations")
    op.drop_index("ix_external_operations_status", table_name="external_operations")
    op.drop_index("ix_external_operations_operation_type", table_name="external_operations")
    op.drop_index("ix_external_operations_store_id", table_name="external_operations")
    op.drop_table("external_operations")
