"""market_data: the stored IBKR daily closes of the IBKR stock split check (market_data.md section 8.8.3.1)

Revision ID: c4e8a1f7b2d6
Revises: e5c3a7f1b2d9
"""

from alembic import op

revision = "c4e8a1f7b2d6"
down_revision = "e5c3a7f1b2d9"


def upgrade() -> None:
    op.execute("""
    -- The read step stores the IBKR daily closes once. The report step and the apply step use them and send no IBKR
    -- request. An instrument is read while read_end_utc is not earlier than check_end_utc. has_ibkr_closes is false
    -- when IBKR has no daily bars of the instrument: the apply step uses the detection rule.
    ALTER TABLE ibkr_split_check ADD COLUMN read_end_utc timestamptz, ADD COLUMN has_ibkr_closes boolean;

    CREATE TABLE ibkr_daily_close (
        symbol text NOT NULL,
        exchange text NOT NULL,
        currency text NOT NULL,
        day date NOT NULL,
        close numeric NOT NULL,
        PRIMARY KEY (symbol, exchange, currency, day)
    );
    """)


def downgrade() -> None:
    op.execute("""
    DROP TABLE ibkr_daily_close;
    ALTER TABLE ibkr_split_check DROP COLUMN read_end_utc, DROP COLUMN has_ibkr_closes;
    """)
