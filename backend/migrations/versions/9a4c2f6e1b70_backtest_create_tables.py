"""backtest: create the backtest, backtest_equity_point, and backtest_trade tables

Revision ID: 9a4c2f6e1b70
Revises: 5b2d8e7f4a61
"""

from alembic import op

revision = "9a4c2f6e1b70"
down_revision = "5b2d8e7f4a61"


def upgrade() -> None:
    op.execute("""
    -- One row for each backtest request. The child process writes the metrics when the backtest finishes.
    -- strategy_version_id has no ON DELETE action: a strategy that a backtest uses cannot be deleted
    -- (docs/architecture/strategy.md section 9.1).
    CREATE TABLE backtest (
        id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        strategy_version_id bigint NOT NULL REFERENCES strategy_version (id),
        symbol text NOT NULL,
        exchange text NOT NULL,
        currency text NOT NULL,
        bar_period text NOT NULL,
        start_utc timestamptz NOT NULL,
        end_utc timestamptz NOT NULL,
        paper_capital_usd numeric NOT NULL CHECK (paper_capital_usd > 0),
        status text NOT NULL CHECK (status IN ('queued', 'running', 'finished', 'failed', 'timed_out')),
        error_message text,
        created_at_utc timestamptz NOT NULL,
        started_at_utc timestamptz,
        ended_at_utc timestamptz,
        final_equity_usd numeric,
        total_return_percent numeric,
        max_drawdown_percent numeric,
        trade_count integer,
        CHECK (start_utc < end_utc)
    );

    CREATE INDEX backtest_status ON backtest (status, id);

    CREATE TABLE backtest_equity_point (
        backtest_id bigint NOT NULL REFERENCES backtest (id) ON DELETE CASCADE,
        time_utc timestamptz NOT NULL,
        equity_usd numeric NOT NULL,
        PRIMARY KEY (backtest_id, time_utc)
    );

    CREATE TABLE backtest_trade (
        id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        backtest_id bigint NOT NULL REFERENCES backtest (id) ON DELETE CASCADE,
        time_utc timestamptz NOT NULL,
        side text NOT NULL CHECK (side IN ('BUY', 'SELL')),
        quantity_shares numeric NOT NULL,
        price_usd numeric NOT NULL,
        commission_usd numeric NOT NULL
    );

    CREATE INDEX backtest_trade_backtest ON backtest_trade (backtest_id, time_utc);
    """)


def downgrade() -> None:
    op.execute("""
    DROP TABLE backtest_trade;
    DROP TABLE backtest_equity_point;
    DROP TABLE backtest;
    """)
