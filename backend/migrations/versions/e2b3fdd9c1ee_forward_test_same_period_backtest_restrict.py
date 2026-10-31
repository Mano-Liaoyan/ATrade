"""forward_test: the same-period backtest of a forward test cannot be deleted

Revision ID: e2b3fdd9c1ee
Revises: f66ac656f66b
"""

from alembic import op

revision = "e2b3fdd9c1ee"
down_revision = "f66ac656f66b"


def upgrade() -> None:
    op.execute("""
    -- DELETE /api/backtests/{backtest_id} refuses the same-period backtest of a forward test (409,
    -- docs/architecture/backtest.md section 10.5). The foreign key refuses the delete, so the backtest capability
    -- does not read this table.
    ALTER TABLE forward_test_same_period_backtest
        DROP CONSTRAINT forward_test_same_period_backtest_backtest_id_fkey,
        ADD CONSTRAINT forward_test_same_period_backtest_backtest_id_fkey
            FOREIGN KEY (backtest_id) REFERENCES backtest (id) ON DELETE RESTRICT;
    """)


def downgrade() -> None:
    op.execute("""
    ALTER TABLE forward_test_same_period_backtest
        DROP CONSTRAINT forward_test_same_period_backtest_backtest_id_fkey,
        ADD CONSTRAINT forward_test_same_period_backtest_backtest_id_fkey
            FOREIGN KEY (backtest_id) REFERENCES backtest (id) ON DELETE CASCADE;
    """)
