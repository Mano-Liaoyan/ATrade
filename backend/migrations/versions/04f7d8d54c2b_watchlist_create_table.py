"""watchlist: create the watchlist_instrument table

Revision ID: 04f7d8d54c2b
Revises: 7c1e4a2b9d30
"""

from alembic import op

revision = "04f7d8d54c2b"
down_revision = "7c1e4a2b9d30"


def upgrade() -> None:
    op.execute("""
    -- One row for each instrument that the user saves. An instrument is in the watchlist at most once.
    CREATE TABLE watchlist_instrument (
        id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        symbol text NOT NULL CHECK (char_length(symbol) BETWEEN 1 AND 32),
        exchange text NOT NULL CHECK (char_length(exchange) BETWEEN 1 AND 32),
        currency text NOT NULL CHECK (char_length(currency) BETWEEN 1 AND 8),
        added_at_utc timestamptz NOT NULL,
        UNIQUE (symbol, exchange, currency)
    );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE watchlist_instrument;")
