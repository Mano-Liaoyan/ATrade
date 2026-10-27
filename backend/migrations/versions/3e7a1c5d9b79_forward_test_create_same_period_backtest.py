"""forward_test: create the forward_test_same_period_backtest table

Revision ID: 3e7a1c5d9b79
Revises: 3e7a1c5d9b78
"""

from alembic import op

revision = "3e7a1c5d9b79"
down_revision = "3e7a1c5d9b78"


def upgrade() -> None:
    op.execute("""
    -- The backtests that "Backtest the same period" started for a forward test (docs/architecture/forward_test.md
    -- section 12.10). The forward test page links to the comparison with each of them.
    CREATE TABLE forward_test_same_period_backtest (
        forward_test_id bigint NOT NULL REFERENCES forward_test (id) ON DELETE CASCADE,
        backtest_id bigint NOT NULL REFERENCES backtest (id) ON DELETE CASCADE,
        PRIMARY KEY (forward_test_id, backtest_id)
    );
    """)


def downgrade() -> None:
    op.execute("""
    DROP TABLE forward_test_same_period_backtest;
    """)
