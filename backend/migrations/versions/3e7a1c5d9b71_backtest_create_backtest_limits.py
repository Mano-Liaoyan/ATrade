"""backtest: create the backtest_limits table

Revision ID: 3e7a1c5d9b71
Revises: 9a4c2f6e1b70
"""

from alembic import op

revision = "3e7a1c5d9b71"
down_revision = "9a4c2f6e1b70"


def upgrade() -> None:
    op.execute("""
    -- At most one row: the backtest timeout and concurrency that the user set in the UI.
    -- Without a row, the defaults of backtest/backtest_limits.py apply (120 minutes, 1 backtest).
    CREATE TABLE backtest_limits (
        single_row boolean PRIMARY KEY DEFAULT true CHECK (single_row),
        timeout_seconds integer NOT NULL CHECK (timeout_seconds > 0),
        concurrency integer NOT NULL CHECK (concurrency > 0)
    );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE backtest_limits;")
