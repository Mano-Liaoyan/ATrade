"""forward_test: create the forward_test table

Revision ID: 3e7a1c5d9b76
Revises: 3e7a1c5d9b71
"""

from alembic import op

revision = "3e7a1c5d9b76"
down_revision = "3e7a1c5d9b71"


def upgrade() -> None:
    op.execute("""
    -- One row for each forward test (docs/architecture.md section 12). The Web process inserts the row and writes
    -- only desired_state after that. The forward-test worker writes status and client_id. The child process writes
    -- start_balance_usd and error_message.
    -- strategy_version_id has no ON DELETE action: a strategy that a forward test uses cannot be deleted.
    CREATE TABLE forward_test (
        id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        strategy_version_id bigint NOT NULL REFERENCES strategy_version (id),
        symbol text NOT NULL,
        exchange text NOT NULL,
        currency text NOT NULL,
        bar_period text NOT NULL,
        desired_state text NOT NULL CHECK (desired_state IN ('running', 'stopped')),
        status text NOT NULL
            CHECK (status IN ('starting', 'running', 'stopping', 'stopped', 'stop_failed', 'failed')),
        -- The IB client ID of the child process. NULL after the orders are cancelled and the process ended.
        client_id integer UNIQUE,
        start_balance_usd numeric,
        error_message text,
        created_at_utc timestamptz NOT NULL,
        stopped_at_utc timestamptz
    );

    -- Only 1 forward test can hold a client ID on one instrument (section 12.2).
    CREATE UNIQUE INDEX forward_test_one_per_instrument ON forward_test (symbol, exchange) WHERE client_id IS NOT NULL;
    """)


def downgrade() -> None:
    op.execute("""
    DROP TABLE forward_test;
    """)
