"""backtest: the source order and the bar count of each bar source of a backtest

Revision ID: 2f6b8d1c4e97
Revises: 8d4b2e6f1a90
"""

from alembic import op

revision = "2f6b8d1c4e97"
down_revision = "8d4b2e6f1a90"


def upgrade() -> None:
    op.execute("""
    -- docs/architecture/backtest.md sections 10.2.1 and 10.12. Existing rows stay null.
    ALTER TABLE backtest ADD COLUMN source_order jsonb;
    ALTER TABLE backtest ADD COLUMN bar_count_by_source jsonb;
    """)


def downgrade() -> None:
    op.execute("""
    ALTER TABLE backtest DROP COLUMN bar_count_by_source;
    ALTER TABLE backtest DROP COLUMN source_order;
    """)
