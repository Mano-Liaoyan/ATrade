"""backtest: the copy of the screen and the rebalance period of a `screen` universe

Revision ID: 4dbfcca36529
Revises: 4ae1ad32c14d
"""

from alembic import op

revision = "4dbfcca36529"
down_revision = "4ae1ad32c14d"


def upgrade() -> None:
    op.execute("""
    -- docs/architecture/backtest.md sections 10.2.1 and 10.10.2. The copy of the screen keeps an old backtest the same
    -- after a change or a delete of the screen: no foreign key.
    ALTER TABLE backtest ADD COLUMN universe_screen jsonb;
    ALTER TABLE backtest ADD COLUMN universe_rebalance_period text
        CHECK (universe_rebalance_period IN ('quarter', 'month'));
    ALTER TABLE backtest ADD CONSTRAINT backtest_screen_universe_fields CHECK (
        (universe_kind = 'screen') = (universe_screen IS NOT NULL)
        AND (universe_kind = 'screen') = (universe_rebalance_period IS NOT NULL)
    );
    """)


def downgrade() -> None:
    op.execute("""
    -- The old table cannot hold a screen universe.
    DELETE FROM backtest WHERE universe_kind = 'screen';
    ALTER TABLE backtest DROP CONSTRAINT backtest_screen_universe_fields;
    ALTER TABLE backtest DROP COLUMN universe_rebalance_period;
    ALTER TABLE backtest DROP COLUMN universe_screen;
    """)
