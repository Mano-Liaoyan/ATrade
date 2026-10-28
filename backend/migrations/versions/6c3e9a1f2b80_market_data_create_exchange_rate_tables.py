"""market_data: create the exchange_rate and exchange_rate_saved_range tables

Revision ID: 6c3e9a1f2b80
Revises: 3e7a1c5d9b79
"""

from alembic import op

revision = "6c3e9a1f2b80"
down_revision = "3e7a1c5d9b79"


def upgrade() -> None:
    op.execute("""
    -- The daily IBKR forex rates in USD: usd_per_unit USD for 1 currency unit at the close of the day
    -- (docs/architecture/market_data.md section 8.6). A backtest converts its results to USD with them.
    CREATE TABLE exchange_rate (
        currency text NOT NULL,
        day_start_utc timestamptz NOT NULL,
        usd_per_unit numeric NOT NULL CHECK (usd_per_unit > 0),
        PRIMARY KEY (currency, day_start_utc)
    );

    -- The time ranges that ATrade read from IBKR. A range can have no rates, for example a weekend.
    -- Ranges of one currency do not overlap and do not touch: the store joins them.
    CREATE TABLE exchange_rate_saved_range (
        id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        currency text NOT NULL,
        start_utc timestamptz NOT NULL,
        end_utc timestamptz NOT NULL,
        CHECK (start_utc < end_utc)
    );

    CREATE INDEX exchange_rate_saved_range_lookup ON exchange_rate_saved_range (currency, start_utc);
    """)


def downgrade() -> None:
    op.execute("""
    DROP TABLE exchange_rate_saved_range;
    DROP TABLE exchange_rate;
    """)
