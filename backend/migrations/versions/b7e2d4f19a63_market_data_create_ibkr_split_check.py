"""market_data: the ibkr_split_check table of docs/architecture/market_data.md section 8.8.3

Revision ID: b7e2d4f19a63
Revises: a3f9d2c7e514
"""

from alembic import op

revision = "b7e2d4f19a63"
down_revision = "a3f9d2c7e514"


def upgrade() -> None:
    op.execute("""
    -- One row for each Databento instrument that still trades. The IBKR stock split check program compares its
    -- Databento closes with the IBKR closes. The instrument waits for the check while checked_end_utc is NULL or
    -- earlier than check_end_utc.
    CREATE TABLE ibkr_split_check (
        symbol text NOT NULL,
        exchange text NOT NULL,
        currency text NOT NULL,
        check_end_utc timestamptz NOT NULL,
        checked_end_utc timestamptz,
        checked_at_utc timestamptz,
        PRIMARY KEY (symbol, exchange, currency)
    );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE ibkr_split_check;")
