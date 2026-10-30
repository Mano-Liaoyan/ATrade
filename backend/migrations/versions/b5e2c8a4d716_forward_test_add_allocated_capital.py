"""forward_test: add allocated_capital_usd and drop forward_test_one_per_instrument

Revision ID: b5e2c8a4d716
Revises: 8d4f2a6c1e93, c7a3e1f95b24
"""

from alembic import op

revision = "b5e2c8a4d716"
# This revision also joins the 2 heads before it: strategy (#171) and the owner ledger (#214).
down_revision = ("8d4f2a6c1e93", "c7a3e1f95b24")


def upgrade() -> None:
    # The allocated capital of a forward test (docs/architecture/forward_test.md section 12.18). The Web process
    # writes it for each new row. Old rows keep null and their start_balance_usd (section 12.24).
    # Forward tests can share an instrument (section 12.2), so the partial unique index goes away.
    op.execute("""
    ALTER TABLE forward_test ADD COLUMN allocated_capital_usd numeric CHECK (allocated_capital_usd > 0);
    DROP INDEX forward_test_one_per_instrument;
    """)


def downgrade() -> None:
    op.execute("""
    CREATE UNIQUE INDEX forward_test_one_per_instrument ON forward_test (symbol, exchange) WHERE client_id IS NOT NULL;
    ALTER TABLE forward_test DROP COLUMN allocated_capital_usd;
    """)
