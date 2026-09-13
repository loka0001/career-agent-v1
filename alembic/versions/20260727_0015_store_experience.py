"""Store profile, assistant configuration, and onboarding progress."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260727_0015"
down_revision: str | None = "20260727_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "store_settings",
        sa.Column("store_id", sa.String(64), sa.ForeignKey("stores.id"), primary_key=True),
        sa.Column("business_type", sa.String(80), nullable=False),
        sa.Column("logo_url", sa.Text(), nullable=True),
        sa.Column("brand_colors_json", sa.JSON(), nullable=False),
        sa.Column("tone", sa.String(40), nullable=False),
        sa.Column("assistant_name", sa.String(100), nullable=False),
        sa.Column("assistant_instructions", sa.Text(), nullable=False),
        sa.Column("shipping_policy", sa.Text(), nullable=False),
        sa.Column("return_policy", sa.Text(), nullable=False),
        sa.Column("onboarding_steps_json", sa.JSON(), nullable=False),
        sa.Column("onboarding_completed", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("store_settings")
