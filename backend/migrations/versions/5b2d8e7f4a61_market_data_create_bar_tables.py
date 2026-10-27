"""market_data: create the bar and bar_saved_range tables

Revision ID: 5b2d8e7f4a61
Revises: 04f7d8d54c2b
"""

from alembic import op

revision = "5b2d8e7f4a61"
down_revision = "04f7d8d54c2b"


def upgrade() -> None:
    op.execute("""
    -- No partitions, no BRIN index, and no compression (docs/architecture/market_data.md section 8.1).
    CREATE TABLE bar (
        symbol text NOT NULL,
        exchange text NOT NULL,
        currency text NOT NULL,
        bar_period text NOT NULL,
        start_utc timestamptz NOT NULL,
        open numeric NOT NULL,
        high numeric NOT NULL,
        low numeric NOT NULL,
        close numeric NOT NULL,
        volume numeric NOT NULL,
        PRIMARY KEY (symbol, exchange, currency, bar_period, start_utc)
    );

    -- The time ranges that ATrade read from IBKR. A range can have no bars, for example a weekend.
    -- Ranges of one instrument and bar period do not overlap and do not touch: the store joins them.
    CREATE TABLE bar_saved_range (
        id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        symbol text NOT NULL,
        exchange text NOT NULL,
        currency text NOT NULL,
        bar_period text NOT NULL,
        start_utc timestamptz NOT NULL,
        end_utc timestamptz NOT NULL,
        CHECK (start_utc < end_utc)
    );

    CREATE INDEX bar_saved_range_lookup ON bar_saved_range (symbol, exchange, currency, bar_period, start_utc);
    """)


def downgrade() -> None:
    op.execute("""
    DROP TABLE bar_saved_range;
    DROP TABLE bar;
    """)
