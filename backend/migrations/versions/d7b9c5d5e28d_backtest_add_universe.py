"""backtest: the universe of a multi-instrument backtest and the instrument of each trade

Revision ID: d7b9c5d5e28d
Revises: bac389eabc50
"""

from alembic import op

revision = "d7b9c5d5e28d"
down_revision = "bac389eabc50"


def upgrade() -> None:
    op.execute("""
    -- docs/architecture/backtest.md sections 10.2.1 and 10.10. Existing rows get the kind 'single'.
    ALTER TABLE backtest ALTER COLUMN symbol DROP NOT NULL;
    ALTER TABLE backtest ALTER COLUMN exchange DROP NOT NULL;
    ALTER TABLE backtest ALTER COLUMN currency DROP NOT NULL;
    ALTER TABLE backtest ADD COLUMN universe_kind text NOT NULL DEFAULT 'single'
        CHECK (universe_kind IN ('single', 'rule', 'list', 'screen'));
    ALTER TABLE backtest ADD COLUMN universe_top_n integer CHECK (universe_top_n BETWEEN 1 AND 500);

    -- One row for each member of the universe in each universe period.
    CREATE TABLE backtest_universe_member (
        backtest_id bigint NOT NULL REFERENCES backtest (id) ON DELETE CASCADE,
        period_start_utc timestamptz NOT NULL,
        symbol text NOT NULL,
        exchange text NOT NULL,
        PRIMARY KEY (backtest_id, period_start_utc, symbol, exchange)
    );

    -- The real exchange, not the simulated venue SMART (ADR 0003). Null on trades from before this migration.
    ALTER TABLE backtest_trade ADD COLUMN symbol text;
    ALTER TABLE backtest_trade ADD COLUMN exchange text;
    """)


def downgrade() -> None:
    op.execute("""
    ALTER TABLE backtest_trade DROP COLUMN exchange;
    ALTER TABLE backtest_trade DROP COLUMN symbol;
    DROP TABLE backtest_universe_member;
    -- A multi-instrument backtest has no instrument, so the old table cannot hold it.
    DELETE FROM backtest WHERE universe_kind <> 'single';
    ALTER TABLE backtest DROP COLUMN universe_top_n;
    ALTER TABLE backtest DROP COLUMN universe_kind;
    ALTER TABLE backtest ALTER COLUMN currency SET NOT NULL;
    ALTER TABLE backtest ALTER COLUMN exchange SET NOT NULL;
    ALTER TABLE backtest ALTER COLUMN symbol SET NOT NULL;
    """)
