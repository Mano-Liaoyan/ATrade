"""forward_test: create the forward_test_fill and forward_test_equity_point tables

Revision ID: 3e7a1c5d9b78
Revises: 3e7a1c5d9b77
"""

from alembic import op

revision = "3e7a1c5d9b78"
down_revision = "3e7a1c5d9b77"


def upgrade() -> None:
    op.execute("""
    -- The records of a forward test (docs/architecture/forward_test.md section 12.8). Only the platform DataActor of
    -- the child process writes them, at the end of each bar. A restart can read the same fill and the same bar again,
    -- so the unique keys make each write idempotent (ON CONFLICT DO NOTHING).
    CREATE TABLE forward_test_fill (
        forward_test_id bigint NOT NULL REFERENCES forward_test (id) ON DELETE CASCADE,
        -- The NautilusTrader TradeId of the fill.
        trade_id text NOT NULL,
        time_utc timestamptz NOT NULL,
        side text NOT NULL CHECK (side IN ('BUY', 'SELL')),
        quantity_shares numeric NOT NULL,
        price_usd numeric NOT NULL,
        commission_usd numeric NOT NULL,
        PRIMARY KEY (forward_test_id, trade_id)
    );

    -- One row at the end of each bar: the start balance plus the cash of the fills plus the position at the close.
    CREATE TABLE forward_test_equity_point (
        forward_test_id bigint NOT NULL REFERENCES forward_test (id) ON DELETE CASCADE,
        time_utc timestamptz NOT NULL,
        equity_usd numeric NOT NULL,
        PRIMARY KEY (forward_test_id, time_utc)
    );
    """)


def downgrade() -> None:
    op.execute("""
    DROP TABLE forward_test_equity_point;
    DROP TABLE forward_test_fill;
    """)
