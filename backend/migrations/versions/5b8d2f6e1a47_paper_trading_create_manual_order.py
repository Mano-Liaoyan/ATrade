"""paper_trading: create the manual_order table

Revision ID: 5b8d2f6e1a47
Revises: 5b2d8e7f4a61
"""

from alembic import op

revision = "5b8d2f6e1a47"
down_revision = "5b2d8e7f4a61"


def upgrade() -> None:
    # Only paper orders that ATrade sent by hand. No status column: IBKR is the only source of order status
    # (docs/architecture/paper_trading.md section 11.4).
    op.execute("""
    CREATE TABLE manual_order (
        id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        created_at_utc timestamptz NOT NULL,
        account text NOT NULL,
        symbol text NOT NULL,
        exchange text NOT NULL,
        currency text NOT NULL,
        side text NOT NULL CHECK (side IN ('BUY', 'SELL')),
        quantity integer NOT NULL CHECK (quantity > 0),
        order_type text NOT NULL CHECK (order_type IN ('MKT', 'LMT')),
        limit_price numeric CHECK (limit_price > 0),
        time_in_force text NOT NULL CHECK (time_in_force IN ('DAY', 'GTC')),
        ibkr_order_id integer NOT NULL,
        CHECK ((order_type = 'LMT') = (limit_price IS NOT NULL))
    );

    CREATE INDEX manual_order_ibkr_order_id ON manual_order (ibkr_order_id);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE manual_order;")
