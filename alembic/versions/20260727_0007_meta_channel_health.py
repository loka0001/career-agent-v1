"""Meta channel token-health metadata."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260727_0007"
down_revision: str | None = "20260727_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("channels") as batch:
        batch.add_column(sa.Column("permissions_json", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("last_check_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("channels") as batch:
        batch.drop_column("last_check_at")
        batch.drop_column("token_expires_at")
        batch.drop_column("permissions_json")
