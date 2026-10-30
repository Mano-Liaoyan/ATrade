"""market_data: the stock_split table and the databento_symbol_link table

Revision ID: 20a1ab3c3c30
Revises: 4a6c8e1b3d57
"""

from alembic import op

revision = "20a1ab3c3c30"
down_revision = "4a6c8e1b3d57"


def upgrade() -> None:
    op.execute("""
    -- One row for each stock split (docs/architecture/market_data.md section 8.13.1). A NULL confirmation is a
    -- stock split of the Databento import that waits for the user check (section 8.8.3).
    CREATE TABLE stock_split (
        id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        symbol text NOT NULL,
        exchange text NOT NULL,
        currency text NOT NULL,
        ex_date_utc timestamptz NOT NULL,
        split_ratio numeric NOT NULL CHECK (split_ratio > 0),
        source text NOT NULL CHECK (source IN ('ibkr_evidence', 'databento_import')),
        confirmation text CHECK (
            confirmation IN ('both_evidences', 'bar_evidence', 'user_apply', 'import_check', 'import_rejected')
        ),
        recorded_at_utc timestamptz NOT NULL,
        UNIQUE (symbol, exchange, currency, ex_date_utc)
    );

    -- The symbol changes that the Databento import found (section 8.8.4).
    CREATE TABLE databento_symbol_link (
        id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        old_symbol text NOT NULL,
        new_symbol text NOT NULL,
        exchange text NOT NULL,
        change_day date NOT NULL,
        checked_at_utc timestamptz,
        UNIQUE (old_symbol, new_symbol, exchange, change_day)
    );
    """)


def downgrade() -> None:
    op.execute("""
    DROP TABLE databento_symbol_link;
    DROP TABLE stock_split;
    """)
