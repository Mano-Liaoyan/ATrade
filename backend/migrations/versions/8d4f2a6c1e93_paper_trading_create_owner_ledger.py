"""paper_trading: create the owner_ledger_entry table

Revision ID: 8d4f2a6c1e93
Revises: 6c3e9a1f2b80
"""

from alembic import op

revision = "8d4f2a6c1e93"
down_revision = "6c3e9a1f2b80"


def upgrade() -> None:
    # The owner ledger (docs/architecture/paper_trading.md section 11.10). A migration cannot read IBKR, so the Web
    # process writes the `ledger_start` rows at the first passed paper account check (section 11.13).
    # `cash_change` is USD. A cash row (the start cash) has no instrument and `quantity_change` 0.
    op.execute("""
    CREATE TABLE owner_ledger_entry (
        id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        owner_kind text NOT NULL CHECK (owner_kind IN ('by_hand', 'forward_test')),
        forward_test_id bigint,
        entry_kind text NOT NULL CHECK (entry_kind IN ('fill', 'split_adjustment', 'transfer', 'ledger_start')),
        time_utc timestamptz NOT NULL,
        account text NOT NULL,
        symbol text,
        exchange text,
        currency text NOT NULL,
        quantity_change numeric NOT NULL,
        price numeric,
        commission numeric NOT NULL DEFAULT 0,
        cash_change numeric NOT NULL,
        ibkr_execution_id text,
        ibkr_order_id integer,
        stock_split_id bigint,
        CHECK ((owner_kind = 'forward_test') = (forward_test_id IS NOT NULL)),
        CHECK ((symbol IS NULL) = (exchange IS NULL)),
        CHECK (symbol IS NOT NULL OR quantity_change = 0),
        CHECK ((entry_kind = 'split_adjustment') = (stock_split_id IS NOT NULL)),
        CHECK (entry_kind <> 'fill' OR (ibkr_execution_id IS NOT NULL AND price IS NOT NULL))
    );

    CREATE UNIQUE INDEX owner_ledger_entry_ibkr_execution_id ON owner_ledger_entry (ibkr_execution_id)
        WHERE ibkr_execution_id IS NOT NULL;
    CREATE INDEX owner_ledger_entry_account ON owner_ledger_entry (account, id);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE owner_ledger_entry;")
