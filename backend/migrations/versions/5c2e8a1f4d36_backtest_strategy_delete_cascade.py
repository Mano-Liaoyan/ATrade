"""backtest: a strategy delete also deletes its backtests and parameter sweeps

Revision ID: 5c2e8a1f4d36
Revises: d2f6b8a40c71
"""

from alembic import op

revision = "5c2e8a1f4d36"
down_revision = "d2f6b8a40c71"


def upgrade() -> None:
    op.execute("""
    -- DELETE /api/strategies/{strategy_id} deletes the backtests and the parameter sweeps of its versions
    -- (docs/architecture/strategy.md section 9.1). The foreign keys do the delete, so the strategy capability
    -- does not write these tables.
    ALTER TABLE backtest
        DROP CONSTRAINT backtest_strategy_version_id_fkey,
        ADD CONSTRAINT backtest_strategy_version_id_fkey
            FOREIGN KEY (strategy_version_id) REFERENCES strategy_version (id) ON DELETE CASCADE;
    ALTER TABLE parameter_sweep
        DROP CONSTRAINT parameter_sweep_strategy_version_id_fkey,
        ADD CONSTRAINT parameter_sweep_strategy_version_id_fkey
            FOREIGN KEY (strategy_version_id) REFERENCES strategy_version (id) ON DELETE CASCADE;

    -- A queued or running backtest cannot be deleted: a backtest process can read or write it. The trigger also
    -- runs for the cascaded delete of a strategy delete. SQLSTATE 55006 is object_in_use.
    CREATE FUNCTION backtest_refuse_delete_while_active() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        RAISE EXCEPTION 'Backtest #% is %. Wait for its end.', OLD.id, OLD.status USING ERRCODE = '55006';
    END;
    $$;
    CREATE TRIGGER backtest_no_delete_while_active
        BEFORE DELETE ON backtest
        FOR EACH ROW WHEN (OLD.status IN ('queued', 'running'))
        EXECUTE FUNCTION backtest_refuse_delete_while_active();
    """)


def downgrade() -> None:
    op.execute("""
    DROP TRIGGER backtest_no_delete_while_active ON backtest;
    DROP FUNCTION backtest_refuse_delete_while_active();
    ALTER TABLE parameter_sweep
        DROP CONSTRAINT parameter_sweep_strategy_version_id_fkey,
        ADD CONSTRAINT parameter_sweep_strategy_version_id_fkey
            FOREIGN KEY (strategy_version_id) REFERENCES strategy_version (id);
    ALTER TABLE backtest
        DROP CONSTRAINT backtest_strategy_version_id_fkey,
        ADD CONSTRAINT backtest_strategy_version_id_fkey
            FOREIGN KEY (strategy_version_id) REFERENCES strategy_version (id);
    """)
