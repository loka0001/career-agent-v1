"""Add per-store provider connections and one-time OAuth transactions."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260728_0019"
down_revision: str | None = "20260728_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "provider_connections",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("store_id", sa.String(64), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("connection_type", sa.String(60), nullable=False),
        sa.Column("external_account_id", sa.String(255), nullable=True),
        sa.Column("external_business_id", sa.String(255), nullable=True),
        sa.Column("external_resource_id", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(160), nullable=False),
        sa.Column("credentials_json", sa.JSON(), nullable=False),
        sa.Column("scopes_json", sa.JSON(), nullable=False),
        sa.Column("capabilities_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_health_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_successful_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(100), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "store_id",
            "provider",
            "connection_type",
            "external_resource_id",
            name="uq_provider_connection_resource",
        ),
    )
    op.create_index(
        "ix_provider_connections_store_id", "provider_connections", ["store_id"]
    )
    op.create_index(
        "ix_provider_connections_provider", "provider_connections", ["provider"]
    )
    op.create_index(
        "ix_provider_connections_connection_type",
        "provider_connections",
        ["connection_type"],
    )
    op.create_index(
        "ix_provider_connections_status", "provider_connections", ["status"]
    )

    op.create_table(
        "oauth_transactions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("store_id", sa.String(64), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("user_id", sa.String(64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("state_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("nonce_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("result_credentials_json", sa.JSON(), nullable=False),
        sa.Column("result_metadata_json", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_oauth_transactions_provider", "oauth_transactions", ["provider"])
    op.create_index("ix_oauth_transactions_store_id", "oauth_transactions", ["store_id"])
    op.create_index("ix_oauth_transactions_user_id", "oauth_transactions", ["user_id"])
    op.create_index(
        "ix_oauth_transactions_state_hash",
        "oauth_transactions",
        ["state_hash"],
        unique=True,
    )
    op.create_index(
        "ix_oauth_transactions_expires_at", "oauth_transactions", ["expires_at"]
    )

    with op.batch_alter_table("channels") as batch:
        batch.add_column(sa.Column("provider_connection_id", sa.String(64), nullable=True))
        batch.create_foreign_key(
            "fk_channels_provider_connection",
            "provider_connections",
            ["provider_connection_id"],
            ["id"],
        )
        batch.create_index(
            "ix_channels_provider_connection_id", ["provider_connection_id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("channels") as batch:
        batch.drop_index("ix_channels_provider_connection_id")
        batch.drop_constraint("fk_channels_provider_connection", type_="foreignkey")
        batch.drop_column("provider_connection_id")
    op.drop_index("ix_oauth_transactions_expires_at", table_name="oauth_transactions")
    op.drop_index("ix_oauth_transactions_state_hash", table_name="oauth_transactions")
    op.drop_index("ix_oauth_transactions_user_id", table_name="oauth_transactions")
    op.drop_index("ix_oauth_transactions_store_id", table_name="oauth_transactions")
    op.drop_index("ix_oauth_transactions_provider", table_name="oauth_transactions")
    op.drop_table("oauth_transactions")
    op.drop_index("ix_provider_connections_status", table_name="provider_connections")
    op.drop_index(
        "ix_provider_connections_connection_type", table_name="provider_connections"
    )
    op.drop_index("ix_provider_connections_provider", table_name="provider_connections")
    op.drop_index("ix_provider_connections_store_id", table_name="provider_connections")
    op.drop_table("provider_connections")
