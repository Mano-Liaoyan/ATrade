"""paper_trading: create the split_check table

Revision ID: f66ac656f66b
Revises: 78f13d0ee614
"""

from alembic import op

revision = "f66ac656f66b"
down_revision = "78f13d0ee614"


def upgrade() -> None:
    op.execute("""
    -- The "Split check needed" state (docs/architecture/paper_trading.md section 11.11). `stock_split_id` is NULL for
    -- a `position_only` check until "Apply split" writes the stock split. `ex_date_utc` is the ex-date of the stock
    -- split (or the check day for `position_only`). `restarted_at_utc` is set when the worker restarted the forward
    -- tests of the instrument after "Apply split" (section 11.13).
    CREATE TABLE split_check (
        id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        stock_split_id bigint REFERENCES stock_split (id),
        account text NOT NULL,
        symbol text NOT NULL,
        exchange text NOT NULL,
        currency text NOT NULL,
        ex_date_utc timestamptz NOT NULL,
        detected_ratio numeric NOT NULL CHECK (detected_ratio > 0),
        evidence text NOT NULL CHECK (
            evidence IN ('bar_ratio_only', 'position_only', 'ratios_differ', 'share_count_differs', 'unusual_ratio')
        ),
        account_quantity_before numeric NOT NULL,
        account_quantity_after numeric NOT NULL,
        status text NOT NULL CHECK (status IN ('needed', 'applied', 'kept')),
        created_at_utc timestamptz NOT NULL,
        resolved_at_utc timestamptz,
        restarted_at_utc timestamptz,
        CHECK ((status = 'needed') = (resolved_at_utc IS NULL))
    );

    -- At most one "Split check needed" state for each instrument of an account.
    CREATE UNIQUE INDEX split_check_needed ON split_check (account, symbol, exchange, currency)
        WHERE status = 'needed';
    """)


def downgrade() -> None:
    op.execute("DROP TABLE split_check;")
