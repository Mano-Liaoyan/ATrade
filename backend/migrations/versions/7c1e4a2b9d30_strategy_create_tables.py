"""strategy: create the strategy and strategy_version tables

Revision ID: 7c1e4a2b9d30
Revises:
"""

from alembic import op

revision = "7c1e4a2b9d30"
down_revision = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE strategy (
        id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        name text NOT NULL UNIQUE CHECK (char_length(name) BETWEEN 1 AND 100),
        created_at_utc timestamptz NOT NULL
    );

    -- Deleting a strategy deletes its versions. A backtest or forward test row that references a
    -- version (strategy_version_id, NOT NULL, no ON DELETE action) makes that delete fail.
    CREATE TABLE strategy_version (
        id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        strategy_id bigint NOT NULL REFERENCES strategy (id) ON DELETE CASCADE,
        version_number integer NOT NULL CHECK (version_number >= 1),
        code text NOT NULL,
        code_sha256 text NOT NULL,
        created_at_utc timestamptz NOT NULL,
        UNIQUE (strategy_id, version_number)
    );

    -- Strategy versions are append-only (docs/architecture/strategy.md section 1).
    CREATE FUNCTION strategy_version_refuse_update() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        RAISE EXCEPTION 'strategy_version rows are append-only. Save a new version instead.';
    END;
    $$;

    CREATE TRIGGER strategy_version_append_only
        BEFORE UPDATE ON strategy_version
        FOR EACH ROW EXECUTE FUNCTION strategy_version_refuse_update();
    """)


def downgrade() -> None:
    op.execute("""
    DROP TABLE strategy_version;
    DROP FUNCTION strategy_version_refuse_update();
    DROP TABLE strategy;
    """)
