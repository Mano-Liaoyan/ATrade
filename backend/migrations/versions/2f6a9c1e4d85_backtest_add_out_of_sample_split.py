"""backtest: add the in-sample and out-of-sample split of docs/architecture/backtest.md section 10.9.4

Revision ID: 2f6a9c1e4d85
Revises: 8d4b6f2a1c93
"""

from alembic import op

revision = "2f6a9c1e4d85"
down_revision = "8d4b6f2a1c93"


def upgrade() -> None:
    op.execute("""
    -- Existing backtests have no split. The start route sets split_time_utc, and nothing changes it later.
    ALTER TABLE backtest
        ADD COLUMN out_of_sample_share integer NOT NULL DEFAULT 0
            CHECK (out_of_sample_share BETWEEN 0 AND 50),
        ADD COLUMN split_time_utc timestamptz,
        ADD CONSTRAINT backtest_split_time_only_with_a_share
            CHECK ((out_of_sample_share = 0) = (split_time_utc IS NULL));
    """)


def downgrade() -> None:
    op.execute("""
    ALTER TABLE backtest
        DROP CONSTRAINT backtest_split_time_only_with_a_share,
        DROP COLUMN split_time_utc,
        DROP COLUMN out_of_sample_share;
    """)
