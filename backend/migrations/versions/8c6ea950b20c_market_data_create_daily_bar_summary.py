"""market_data: the daily bar summary

Revision ID: 8c6ea950b20c
Revises: cbe826c0a6dd
"""

from alembic import op

revision = "8c6ea950b20c"
down_revision = "cbe826c0a6dd"


def upgrade() -> None:
    op.execute("""
    -- docs/architecture/market_data.md section 8.11. One row for each instrument with daily bars.
    CREATE TABLE daily_bar_summary (
        symbol text NOT NULL,
        exchange text NOT NULL,
        currency text NOT NULL,
        last_day_start_utc timestamptz NOT NULL,
        last_close numeric NOT NULL,
        -- The value of the indicator class average_trading_value(20) (ADR 0001). NULL: fewer than 20 daily bars.
        average_trading_value_20 double precision,
        PRIMARY KEY (symbol, exchange, currency)
    );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE daily_bar_summary;")
