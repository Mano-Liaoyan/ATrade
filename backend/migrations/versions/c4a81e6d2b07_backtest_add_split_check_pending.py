"""backtest: add the stock split check warning of docs/architecture/backtest.md section 10.12

Revision ID: c4a81e6d2b07
Revises: b7e2d4f19a63
"""

from alembic import op

revision = "c4a81e6d2b07"
down_revision = "b7e2d4f19a63"


def upgrade() -> None:
    op.execute("""
    -- True when an instrument of the backtest waited for the IBKR stock split check when the backtest was created.
    ALTER TABLE backtest ADD COLUMN has_split_check_pending boolean NOT NULL DEFAULT false;
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE backtest DROP COLUMN has_split_check_pending;")
