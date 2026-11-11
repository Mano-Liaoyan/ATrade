"""forward_test: a forward test can be deleted, and a strategy delete also deletes its forward tests

Revision ID: 7e4b1d9a2c58
Revises: 5c2e8a1f4d36
"""

from alembic import op

revision = "7e4b1d9a2c58"
down_revision = "5c2e8a1f4d36"


def upgrade() -> None:
    op.execute("""
    -- DELETE /api/forward-tests/{forward_test_id} and the strategy delete (docs/architecture/forward_test.md
    -- section 12.13). The rows of the forward test go with it. The owner ledger rows stay: they are the history of
    -- the paper account, and owner_ledger_entry.forward_test_id has no foreign key.
    ALTER TABLE forward_test
        DROP CONSTRAINT forward_test_strategy_version_id_fkey,
        ADD CONSTRAINT forward_test_strategy_version_id_fkey
            FOREIGN KEY (strategy_version_id) REFERENCES strategy_version (id) ON DELETE CASCADE;
    ALTER TABLE forward_test_interruption
        DROP CONSTRAINT forward_test_interruption_forward_test_id_fkey,
        ADD CONSTRAINT forward_test_interruption_forward_test_id_fkey
            FOREIGN KEY (forward_test_id) REFERENCES forward_test (id) ON DELETE CASCADE;

    -- DELETE /api/backtests/{backtest_id} still refuses the same-period backtest of a forward test: the check is
    -- immediate. The strategy delete defers all constraints of its transaction (SET CONSTRAINTS ALL DEFERRED), so a
    -- cascade that deletes the forward test and the backtest in any order passes. RESTRICT cannot be deferred.
    ALTER TABLE forward_test_same_period_backtest
        DROP CONSTRAINT forward_test_same_period_backtest_backtest_id_fkey,
        ADD CONSTRAINT forward_test_same_period_backtest_backtest_id_fkey
            FOREIGN KEY (backtest_id) REFERENCES backtest (id) DEFERRABLE INITIALLY IMMEDIATE;

    -- Only a forward test that has ended can be deleted: the status is stopped, or failed without a client ID
    -- (the worker skips these rows, section 12.14). The trigger also runs for the cascaded delete of a strategy
    -- delete. SQLSTATE 55006 is object_in_use.
    CREATE FUNCTION forward_test_refuse_delete_while_active() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        RAISE EXCEPTION 'Forward test #% has not ended. Stop it first.', OLD.id USING ERRCODE = '55006';
    END;
    $$;
    CREATE TRIGGER forward_test_no_delete_while_active
        BEFORE DELETE ON forward_test
        FOR EACH ROW WHEN (NOT (OLD.status = 'stopped' OR (OLD.status = 'failed' AND OLD.client_id IS NULL)))
        EXECUTE FUNCTION forward_test_refuse_delete_while_active();
    """)


def downgrade() -> None:
    op.execute("""
    DROP TRIGGER forward_test_no_delete_while_active ON forward_test;
    DROP FUNCTION forward_test_refuse_delete_while_active();
    ALTER TABLE forward_test_same_period_backtest
        DROP CONSTRAINT forward_test_same_period_backtest_backtest_id_fkey,
        ADD CONSTRAINT forward_test_same_period_backtest_backtest_id_fkey
            FOREIGN KEY (backtest_id) REFERENCES backtest (id) ON DELETE RESTRICT;
    ALTER TABLE forward_test_interruption
        DROP CONSTRAINT forward_test_interruption_forward_test_id_fkey,
        ADD CONSTRAINT forward_test_interruption_forward_test_id_fkey
            FOREIGN KEY (forward_test_id) REFERENCES forward_test (id);
    ALTER TABLE forward_test
        DROP CONSTRAINT forward_test_strategy_version_id_fkey,
        ADD CONSTRAINT forward_test_strategy_version_id_fkey
            FOREIGN KEY (strategy_version_id) REFERENCES strategy_version (id);
    """)
