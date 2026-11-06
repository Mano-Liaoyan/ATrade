"""forward_test: drop forward_test_fill, and give the old forward tests an allocated capital

Revision ID: d7b2f4a9c613
Revises: c4a8e1d7f362
"""

from alembic import op

revision = "d7b2f4a9c613"
down_revision = "c4a8e1d7f362"


def upgrade() -> None:
    op.execute("""
    -- The routes read the fills only from the owner ledger (docs/architecture/forward_test.md section 12.24).
    DROP TABLE forward_test_fill;

    -- Only an old row has start_balance_usd. A row with a client ID stays, because its capital would count as allocated.
    UPDATE forward_test SET allocated_capital_usd = start_balance_usd
    WHERE allocated_capital_usd IS NULL AND client_id IS NULL;
    """)


def downgrade() -> None:
    op.execute("""
    UPDATE forward_test SET allocated_capital_usd = NULL WHERE start_balance_usd IS NOT NULL;

    CREATE TABLE forward_test_fill (
        forward_test_id bigint NOT NULL REFERENCES forward_test (id) ON DELETE CASCADE,
        trade_id text NOT NULL,
        time_utc timestamptz NOT NULL,
        side text NOT NULL CHECK (side IN ('BUY', 'SELL')),
        quantity_shares numeric NOT NULL,
        price_usd numeric NOT NULL,
        commission_usd numeric NOT NULL,
        PRIMARY KEY (forward_test_id, trade_id)
    );
    """)
