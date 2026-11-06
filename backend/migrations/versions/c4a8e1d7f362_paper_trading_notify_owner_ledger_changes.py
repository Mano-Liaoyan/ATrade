"""paper_trading: notify the owner_ledger_entry changes, and remove the trigger of forward_test_fill

Revision ID: c4a8e1d7f362
Revises: e5c7a1f4b92d
"""

from alembic import op

revision = "c4a8e1d7f362"
down_revision = "e5c7a1f4b92d"


def upgrade() -> None:
    op.execute("""
    -- The fills of a forward test go to the owner ledger, so /ws/forward-tests watches owner_ledger_entry.
    CREATE TRIGGER notify_table_change AFTER INSERT OR UPDATE OR DELETE OR TRUNCATE ON owner_ledger_entry
    FOR EACH STATEMENT EXECUTE FUNCTION notify_table_change();

    -- No program writes forward_test_fill. The table stays, because the routes read the fills of the old forward
    -- tests from it (docs/architecture/forward_test.md section 12.24).
    DROP TRIGGER notify_table_change ON forward_test_fill;
    """)


def downgrade() -> None:
    op.execute("""
    CREATE TRIGGER notify_table_change AFTER INSERT OR UPDATE OR DELETE OR TRUNCATE ON forward_test_fill
    FOR EACH STATEMENT EXECUTE FUNCTION notify_table_change();

    DROP TRIGGER notify_table_change ON owner_ledger_entry;
    """)
