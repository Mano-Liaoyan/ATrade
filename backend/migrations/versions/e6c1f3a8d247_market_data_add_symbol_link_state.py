"""market_data: the state of a Databento symbol link

Revision ID: e6c1f3a8d247
Revises: a9d3e7c15b42
"""

from alembic import op

revision = "e6c1f3a8d247"
down_revision = "a9d3e7c15b42"


def upgrade() -> None:
    op.execute("""
    -- docs/architecture/market_data.md section 8.8.4. The links before this column moved their bars.
    ALTER TABLE databento_symbol_link
        ADD COLUMN state text NOT NULL DEFAULT 'moved' CHECK (state IN ('moved', 'waiting', 'rejected'));
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE databento_symbol_link DROP COLUMN state;")
