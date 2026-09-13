"""Add privacy workflows, retention policy, private media, and audit tenancy."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260729_0026"
down_revision: str | None = "20260728_0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("deletion_requested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "stores",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "stores",
        sa.Column("deletion_requested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("stores", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_stores_is_active", "stores", ["is_active"])

    op.add_column(
        "media_assets",
        sa.Column("store_id", sa.String(64), sa.ForeignKey("stores.id"), nullable=True),
    )
    op.add_column(
        "media_assets",
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "media_assets",
        sa.Column(
            "purpose",
            sa.String(40),
            nullable=False,
            server_default="legacy_product",
        ),
    )
    op.add_column(
        "media_assets",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_media_assets_store_id", "media_assets", ["store_id"])
    op.create_index("ix_media_assets_is_public", "media_assets", ["is_public"])
    op.create_index("ix_media_assets_purpose", "media_assets", ["purpose"])
    op.create_index("ix_media_assets_expires_at", "media_assets", ["expires_at"])

    for column, foreign_key in (
        ("organization_id", "organizations.id"),
        ("store_id", "stores.id"),
        ("actor_user_id", "users.id"),
    ):
        op.add_column(
            "audit_events",
            sa.Column(column, sa.String(64), sa.ForeignKey(foreign_key), nullable=True),
        )
        op.create_index(f"ix_audit_events_{column}", "audit_events", [column])

    op.create_table(
        "retention_policies",
        sa.Column("store_id", sa.String(64), sa.ForeignKey("stores.id"), primary_key=True),
        sa.Column("message_days", sa.Integer(), nullable=False, server_default="365"),
        sa.Column("media_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("event_days", sa.Integer(), nullable=False, server_default="365"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "data_deletion_requests",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("scope", sa.String(30), nullable=False),
        sa.Column(
            "organization_id",
            sa.String(64),
            sa.ForeignKey("organizations.id"),
            nullable=True,
        ),
        sa.Column("store_id", sa.String(64), sa.ForeignKey("stores.id"), nullable=True),
        sa.Column("user_id", sa.String(64), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=True),
        sa.Column("provider_user_id_hash", sa.String(64), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("execute_after", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
    )
    for column in (
        "scope",
        "organization_id",
        "store_id",
        "user_id",
        "customer_id",
        "status",
        "execute_after",
    ):
        op.create_index(
            f"ix_data_deletion_requests_{column}",
            "data_deletion_requests",
            [column],
        )


def downgrade() -> None:
    op.drop_table("data_deletion_requests")
    op.drop_table("retention_policies")
    for column in ("actor_user_id", "store_id", "organization_id"):
        op.drop_index(f"ix_audit_events_{column}", table_name="audit_events")
        op.drop_column("audit_events", column)
    for index in (
        "ix_media_assets_expires_at",
        "ix_media_assets_purpose",
        "ix_media_assets_is_public",
        "ix_media_assets_store_id",
    ):
        op.drop_index(index, table_name="media_assets")
    op.drop_column("media_assets", "expires_at")
    op.drop_column("media_assets", "purpose")
    op.drop_column("media_assets", "is_public")
    op.drop_column("media_assets", "store_id")
    op.drop_index("ix_stores_is_active", table_name="stores")
    op.drop_column("stores", "deleted_at")
    op.drop_column("stores", "deletion_requested_at")
    op.drop_column("stores", "is_active")
    op.drop_column("users", "deleted_at")
    op.drop_column("users", "deletion_requested_at")
