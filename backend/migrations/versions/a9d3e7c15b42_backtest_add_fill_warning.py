"""backtest: add the fill warning of docs/architecture/backtest.md section 10.10.3

Revision ID: a9d3e7c15b42
Revises: e5c7a1f4b92d
"""

from alembic import op

revision = "a9d3e7c15b42"
down_revision = "e5c7a1f4b92d"


def upgrade() -> None:
    op.execute("""
    -- The run warning when the free cash did not pay for an order at the open. Null without such an order.
    ALTER TABLE backtest ADD COLUMN fill_warning text;
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE backtest DROP COLUMN fill_warning;")
