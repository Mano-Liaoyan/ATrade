"""backtest: add backtest.conversation_id

Revision ID: 4a6c8e1b3d57
Revises: 2f7a9c3e5b14
"""

from alembic import op

revision = "4a6c8e1b3d57"
down_revision = "2f7a9c3e5b14"


def upgrade() -> None:
    op.execute("""
    -- The conversation of a backtest that the AI assistant started (docs/architecture/backtest.md 10.2.1).
    -- A delete of the conversation keeps the backtest and sets the column to null.
    ALTER TABLE backtest ADD COLUMN conversation_id bigint REFERENCES assistant_conversation (id) ON DELETE SET NULL;
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE backtest DROP COLUMN conversation_id;")
