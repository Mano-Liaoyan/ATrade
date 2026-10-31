"""market_data: create the hk_instrument_list_member table

Revision ID: 8d4b1e7c2a90
Revises: 6c3e9a1f2b80
"""

from alembic import op

revision = "8d4b1e7c2a90"
down_revision = "6c3e9a1f2b80"


def upgrade() -> None:
    op.execute("""
    -- One row for each instrument of the HK instrument list, the default universe of an HK screen.
    -- An instrument is in the list at most once.
    CREATE TABLE hk_instrument_list_member (
        id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        symbol text NOT NULL CHECK (char_length(symbol) BETWEEN 1 AND 32),
        exchange text NOT NULL CHECK (exchange = 'SEHK'),
        currency text NOT NULL CHECK (currency = 'HKD'),
        added_at_utc timestamptz NOT NULL,
        UNIQUE (symbol, exchange, currency)
    );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE hk_instrument_list_member;")
