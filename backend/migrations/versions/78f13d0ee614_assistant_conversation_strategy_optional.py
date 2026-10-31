"""assistant: a conversation can start without a strategy

Revision ID: 78f13d0ee614
Revises: 4dbfcca36529
"""

from alembic import op

revision = "78f13d0ee614"
down_revision = "4dbfcca36529"


def upgrade() -> None:
    op.execute("""
    -- docs/architecture/assistant.md 25.8.1: each workbench page has the AI assistant column. A conversation that
    -- starts on a page without an open strategy has no strategy.
    ALTER TABLE assistant_conversation ALTER COLUMN strategy_id DROP NOT NULL;
    """)


def downgrade() -> None:
    op.execute("""
    -- The conversations without a strategy cannot stay. Their JSONL files stay in the volume.
    DELETE FROM assistant_conversation WHERE strategy_id IS NULL;
    ALTER TABLE assistant_conversation ALTER COLUMN strategy_id SET NOT NULL;
    """)
