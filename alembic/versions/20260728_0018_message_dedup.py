"""Enforce provider message idempotency under concurrent webhook delivery."""

from alembic import op

revision = "20260728_0018"
down_revision = "20260727_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM messages
        WHERE id IN (
            SELECT id
            FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY conversation_id, external_id
                           ORDER BY id
                       ) AS duplicate_number
                FROM messages
                WHERE external_id IS NOT NULL
            ) duplicated
            WHERE duplicate_number > 1
        )
        """
    )
    op.create_index(
        "uq_message_conversation_external",
        "messages",
        ["conversation_id", "external_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_message_conversation_external", table_name="messages")
