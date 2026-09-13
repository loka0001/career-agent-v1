"""Add idempotent external product and order mappings."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260728_0023"
down_revision: str | None = "20260728_0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "external_product_mappings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("store_id", sa.String(64), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column(
            "provider_connection_id",
            sa.String(64),
            sa.ForeignKey("provider_connections.id"),
            nullable=False,
        ),
        sa.Column("product_pk", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("external_product_id", sa.String(255), nullable=False),
        sa.Column("external_variant_id", sa.String(255), nullable=False, server_default=""),
        sa.Column("external_sku", sa.String(255), nullable=False, server_default=""),
        sa.Column("external_inventory_id", sa.String(255), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "provider_connection_id",
            "external_product_id",
            "external_variant_id",
            name="uq_external_product_variant",
        ),
    )
    for column in (
        "store_id",
        "provider_connection_id",
        "product_pk",
        "external_product_id",
        "external_sku",
    ):
        op.create_index(
            f"ix_external_product_mappings_{column}",
            "external_product_mappings",
            [column],
        )

    op.create_table(
        "external_order_mappings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("store_id", sa.String(64), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column(
            "provider_connection_id",
            sa.String(64),
            sa.ForeignKey("provider_connections.id"),
            nullable=False,
        ),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("external_order_id", sa.String(255), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "provider_connection_id",
            "external_order_id",
            name="uq_external_order",
        ),
    )
    for column in (
        "store_id",
        "provider_connection_id",
        "order_id",
        "external_order_id",
    ):
        op.create_index(
            f"ix_external_order_mappings_{column}",
            "external_order_mappings",
            [column],
        )


def downgrade() -> None:
    op.drop_table("external_order_mappings")
    op.drop_table("external_product_mappings")
