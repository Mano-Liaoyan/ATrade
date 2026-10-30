"""backtest: the parameter sweep, the sweep and parameters of a backtest, and the status cancelled

Revision ID: b22fc9704bfc
Revises: d7b9c5d5e28d
"""

from alembic import op

revision = "b22fc9704bfc"
down_revision = "d7b9c5d5e28d"


def upgrade() -> None:
    op.execute("""
    -- docs/architecture/backtest.md sections 10.2.1 and 10.11.
    CREATE TABLE parameter_sweep (
        id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        strategy_version_id bigint NOT NULL,
        grid jsonb NOT NULL,
        created_at_utc timestamptz NOT NULL
    );
    ALTER TABLE backtest ADD COLUMN sweep_id bigint REFERENCES parameter_sweep (id);
    ALTER TABLE backtest ADD COLUMN parameters jsonb;
    CREATE INDEX backtest_sweep_id ON backtest (sweep_id);
    ALTER TABLE backtest DROP CONSTRAINT backtest_status_check;
    ALTER TABLE backtest ADD CONSTRAINT backtest_status_check
        CHECK (status IN ('queued', 'running', 'finished', 'failed', 'timed_out', 'cancelled'));
    """)


def downgrade() -> None:
    op.execute("""
    DELETE FROM backtest WHERE sweep_id IS NOT NULL;
    ALTER TABLE backtest DROP CONSTRAINT backtest_status_check;
    ALTER TABLE backtest ADD CONSTRAINT backtest_status_check
        CHECK (status IN ('queued', 'running', 'finished', 'failed', 'timed_out'));
    DROP INDEX backtest_sweep_id;
    ALTER TABLE backtest DROP COLUMN parameters;
    ALTER TABLE backtest DROP COLUMN sweep_id;
    DROP TABLE parameter_sweep;
    """)
