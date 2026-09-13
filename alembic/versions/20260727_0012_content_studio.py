"""Brand voice, campaigns, scheduled content, and version history."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260727_0012"
down_revision: str | None = "20260727_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "store_brands",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("store_id", sa.String(64), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("tone", sa.String(80), nullable=False),
        sa.Column("audience", sa.Text(), nullable=False),
        sa.Column("guidelines", sa.Text(), nullable=False),
        sa.Column("primary_color", sa.String(20), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("store_id"),
    )
    op.create_index("ix_store_brands_store_id", "store_brands", ["store_id"])

    op.create_table(
        "content_campaigns",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("store_id", sa.String(64), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("goal", sa.String(160), nullable=False),
        sa.Column("budget_numeric", sa.Numeric(12, 2), nullable=False),
        sa.Column("product_ids_json", sa.JSON(), nullable=False),
        sa.Column("concept", sa.Text(), nullable=False),
        sa.Column("audience", sa.Text(), nullable=False),
        sa.Column("offer", sa.Text(), nullable=False),
        sa.Column("landing_copy", sa.Text(), nullable=False),
        sa.Column("whatsapp_template", sa.Text(), nullable=False),
        sa.Column("kpis_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_content_campaigns_store_id", "content_campaigns", ["store_id"])

    op.create_table(
        "content_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("store_id", sa.String(64), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("content_campaigns.id"), nullable=True),
        sa.Column("product_id", sa.String(64), nullable=False),
        sa.Column("content_format", sa.String(40), nullable=False),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("tone", sa.String(80), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("caption", sa.Text(), nullable=False),
        sa.Column("hashtags_json", sa.JSON(), nullable=False),
        sa.Column("cta", sa.String(300), nullable=False),
        sa.Column("validation_warnings_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_content_items_store_id", "content_items", ["store_id"])
    op.create_index("ix_content_items_campaign_id", "content_items", ["campaign_id"])
    op.create_index("ix_content_items_status", "content_items", ["status"])
    op.create_index("ix_content_items_scheduled_for", "content_items", ["scheduled_for"])

    op.create_table(
        "content_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("content_item_id", sa.Integer(), sa.ForeignKey("content_items.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot_json", sa.JSON(), nullable=False),
        sa.Column("created_by_user_id", sa.String(64), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("content_item_id", "version", name="uq_content_item_version"),
    )
    op.create_index("ix_content_versions_content_item_id", "content_versions", ["content_item_id"])


def downgrade() -> None:
    op.drop_table("content_versions")
    op.drop_table("content_items")
    op.drop_table("content_campaigns")
    op.drop_table("store_brands")
