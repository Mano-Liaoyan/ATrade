"""market_data: the quarterly US universe

Revision ID: cbe826c0a6dd
Revises: 2f6a9c1e4d85
"""

from alembic import op

revision = "cbe826c0a6dd"
down_revision = "2f6a9c1e4d85"


def upgrade() -> None:
    op.execute("""
    -- docs/architecture/market_data.md section 8.9. One row for each member of each quarter.
    CREATE TABLE us_universe_member (
        quarter_start_utc timestamptz NOT NULL,
        rank integer NOT NULL CHECK (rank BETWEEN 1 AND 500),
        symbol text NOT NULL,
        exchange text NOT NULL,
        currency text NOT NULL,
        average_trading_value numeric NOT NULL,
        last_ranking_day_utc timestamptz NOT NULL,
        PRIMARY KEY (quarter_start_utc, rank),
        -- An instrument is in one quarter at most one time.
        UNIQUE (quarter_start_utc, symbol, exchange, currency)
    );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE us_universe_member;")
