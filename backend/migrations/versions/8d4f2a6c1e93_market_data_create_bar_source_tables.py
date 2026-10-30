"""market_data: one bar table and one saved-range table for each bar source, and the source order

Revision ID: 8d4f2a6c1e93
Revises: 6c3e9a1f2b80
"""

from alembic import op

revision = "8d4f2a6c1e93"
down_revision = "6c3e9a1f2b80"


def upgrade() -> None:
    op.execute("""
    -- The bars of IBKR keep their rows (docs/architecture/market_data.md section 8.7.1, ADR 0002).
    ALTER TABLE bar RENAME TO ibkr_bar;
    ALTER TABLE ibkr_bar RENAME CONSTRAINT bar_pkey TO ibkr_bar_pkey;
    ALTER TABLE bar_saved_range RENAME TO ibkr_bar_saved_range;
    ALTER TABLE ibkr_bar_saved_range RENAME CONSTRAINT bar_saved_range_pkey TO ibkr_bar_saved_range_pkey;
    ALTER SEQUENCE bar_saved_range_id_seq RENAME TO ibkr_bar_saved_range_id_seq;
    ALTER INDEX bar_saved_range_lookup RENAME TO ibkr_bar_saved_range_lookup;

    -- The bars that the Databento import bought. The same columns and primary key as ibkr_bar.
    CREATE TABLE databento_bar (
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

    -- The time ranges that the Databento import bought. A range can have no bars, for example a holiday.
    CREATE TABLE databento_bar_saved_range (
        id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        symbol text NOT NULL,
        exchange text NOT NULL,
        currency text NOT NULL,
        bar_period text NOT NULL,
        start_utc timestamptz NOT NULL,
        end_utc timestamptz NOT NULL,
        CHECK (start_utc < end_utc)
    );

    CREATE INDEX databento_bar_saved_range_lookup
        ON databento_bar_saved_range (symbol, exchange, currency, bar_period, start_utc);

    -- The global source order: 1 row. The first bar source that saved a time range gives its bars.
    CREATE TABLE source_order (
        id boolean PRIMARY KEY DEFAULT true CHECK (id),
        bar_sources text[] NOT NULL,
        changed_at_utc timestamptz NOT NULL
    );

    INSERT INTO source_order (bar_sources, changed_at_utc) VALUES (ARRAY['ibkr', 'databento'], now());
    """)


def downgrade() -> None:
    op.execute("""
    DROP TABLE source_order;
    DROP TABLE databento_bar_saved_range;
    DROP TABLE databento_bar;
    ALTER INDEX ibkr_bar_saved_range_lookup RENAME TO bar_saved_range_lookup;
    ALTER SEQUENCE ibkr_bar_saved_range_id_seq RENAME TO bar_saved_range_id_seq;
    ALTER TABLE ibkr_bar_saved_range RENAME CONSTRAINT ibkr_bar_saved_range_pkey TO bar_saved_range_pkey;
    ALTER TABLE ibkr_bar_saved_range RENAME TO bar_saved_range;
    ALTER TABLE ibkr_bar RENAME CONSTRAINT ibkr_bar_pkey TO bar_pkey;
    ALTER TABLE ibkr_bar RENAME TO bar;
    """)
