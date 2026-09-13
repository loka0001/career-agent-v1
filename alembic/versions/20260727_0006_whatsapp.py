"""WhatsApp Cloud API templates."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260727_0006"
down_revision: str | None = "20260727_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "channel_templates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("store_id", sa.String(64), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("channel_id", sa.Integer(), sa.ForeignKey("channels.id"), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("language", sa.String(16), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("variables_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "store_id",
            "channel_id",
            "name",
            "language",
            name="uq_channel_template_name_language",
        ),
    )
    op.create_index("ix_channel_templates_store_id", "channel_templates", ["store_id"])
    op.create_index("ix_channel_templates_channel_id", "channel_templates", ["channel_id"])
    op.create_index("ix_channel_templates_status", "channel_templates", ["status"])


def downgrade() -> None:
    op.drop_table("channel_templates")
