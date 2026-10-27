"""forward_test: end time, crash count, waiting for IB Gateway, and the interruption table

Revision ID: 3e7a1c5d9b77
Revises: 3e7a1c5d9b76
"""

from alembic import op

revision = "3e7a1c5d9b77"
down_revision = "3e7a1c5d9b76"


def upgrade() -> None:
    op.execute("""
    -- The optional end time (docs/architecture.md section 12.1). The Web process writes it only at the insert.
    ALTER TABLE forward_test ADD COLUMN end_time_utc timestamptz;
    -- The crashes in a row (section 12.7). The worker writes it. At 3 the worker stops the restarts.
    ALTER TABLE forward_test ADD COLUMN crash_count integer NOT NULL DEFAULT 0;

    ALTER TABLE forward_test DROP CONSTRAINT forward_test_status_check;
    ALTER TABLE forward_test ADD CONSTRAINT forward_test_status_check CHECK (
        status IN ('starting', 'running', 'waiting_for_gateway', 'stopping', 'stopped', 'stop_failed', 'failed')
    );

    -- One row for each interruption of a forward test (section 12.7). ended_at_utc is NULL while it lasts.
    CREATE TABLE forward_test_interruption (
        id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        forward_test_id bigint NOT NULL REFERENCES forward_test (id),
        reason text NOT NULL CHECK (reason IN ('crash', 'gateway', 'worker_restart')),
        started_at_utc timestamptz NOT NULL,
        ended_at_utc timestamptz
    );

    -- Only 1 open interruption for each forward test.
    CREATE UNIQUE INDEX forward_test_interruption_one_open
        ON forward_test_interruption (forward_test_id) WHERE ended_at_utc IS NULL;
    """)


def downgrade() -> None:
    op.execute("""
    DROP TABLE forward_test_interruption;
    UPDATE forward_test SET status = 'running' WHERE status = 'waiting_for_gateway';
    ALTER TABLE forward_test DROP CONSTRAINT forward_test_status_check;
    ALTER TABLE forward_test ADD CONSTRAINT forward_test_status_check
        CHECK (status IN ('starting', 'running', 'stopping', 'stopped', 'stop_failed', 'failed'));
    ALTER TABLE forward_test DROP COLUMN crash_count;
    ALTER TABLE forward_test DROP COLUMN end_time_utc;
    """)
