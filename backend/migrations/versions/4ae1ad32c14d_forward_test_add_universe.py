"""forward_test: the universe of a multi-instrument forward test and its members of each quarter

Revision ID: 4ae1ad32c14d
Revises: b22fc9704bfc
"""

from alembic import op

revision = "4ae1ad32c14d"
down_revision = "b22fc9704bfc"


def upgrade() -> None:
    op.execute("""
    -- docs/architecture/forward_test.md section 12.12. Existing rows get the kind 'single'.
    ALTER TABLE forward_test ALTER COLUMN symbol DROP NOT NULL;
    ALTER TABLE forward_test ALTER COLUMN exchange DROP NOT NULL;
    ALTER TABLE forward_test ALTER COLUMN currency DROP NOT NULL;
    ALTER TABLE forward_test ADD COLUMN universe_kind text NOT NULL DEFAULT 'single'
        CHECK (universe_kind IN ('single', 'rule', 'list'));
    ALTER TABLE forward_test ADD COLUMN universe_top_n integer CHECK (universe_top_n BETWEEN 1 AND 500);
    ALTER TABLE forward_test ADD CONSTRAINT forward_test_universe_fields CHECK (
        (universe_kind = 'single') = (symbol IS NOT NULL AND exchange IS NOT NULL AND currency IS NOT NULL)
        AND (universe_kind = 'rule') = (universe_top_n IS NOT NULL)
    );

    -- One row for each member that the forward test gave the strategy in that quarter.
    CREATE TABLE forward_test_universe_member (
        forward_test_id bigint NOT NULL REFERENCES forward_test (id) ON DELETE CASCADE,
        quarter_start_utc timestamptz NOT NULL,
        symbol text NOT NULL,
        exchange text NOT NULL,
        currency text NOT NULL,
        PRIMARY KEY (forward_test_id, quarter_start_utc, symbol, exchange)
    );
    """)


def downgrade() -> None:
    op.execute("""
    DROP TABLE forward_test_universe_member;
    -- A multi-instrument forward test has no instrument, so the old table cannot hold it.
    DELETE FROM forward_test WHERE universe_kind <> 'single';
    ALTER TABLE forward_test DROP CONSTRAINT forward_test_universe_fields;
    ALTER TABLE forward_test DROP COLUMN universe_top_n;
    ALTER TABLE forward_test DROP COLUMN universe_kind;
    ALTER TABLE forward_test ALTER COLUMN currency SET NOT NULL;
    ALTER TABLE forward_test ALTER COLUMN exchange SET NOT NULL;
    ALTER TABLE forward_test ALTER COLUMN symbol SET NOT NULL;
    """)
