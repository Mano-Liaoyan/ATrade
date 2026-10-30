"""screen: create the screen, screen_result, screen_result_row, and screen_result_exclusion tables

Revision ID: d41ce3053ba2
Revises: 2f6b8d1c4e97
"""

from alembic import op

revision = "d41ce3053ba2"
down_revision = "2f6b8d1c4e97"


def upgrade() -> None:
    op.execute("""
    -- The tables of docs/architecture/screen.md section 24.4.
    -- assistant_conversation_id is null for a screen or a run of the user. A delete of the conversation keeps the
    -- screens and the screen results (ON DELETE SET NULL).
    -- kept: true for a screen of the user, false for a screen of the AI assistant until the user selects Keep.
    CREATE TABLE screen (
        id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        name text NOT NULL UNIQUE CHECK (char_length(name) BETWEEN 1 AND 100),
        market text NOT NULL CHECK (market IN ('US', 'HK')),
        definition jsonb NOT NULL,
        assistant_conversation_id bigint REFERENCES assistant_conversation (id) ON DELETE SET NULL,
        kept boolean NOT NULL,
        created_at_utc timestamptz NOT NULL,
        updated_at_utc timestamptz NOT NULL
    );

    -- A delete of a screen deletes its screen results. A backtest keeps its own copy of the screen.
    CREATE TABLE screen_result (
        id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        screen_id bigint NOT NULL REFERENCES screen (id) ON DELETE CASCADE,
        run_at_utc timestamptz NOT NULL,
        definition jsonb NOT NULL,
        market text NOT NULL CHECK (market IN ('US', 'HK')),
        daily_bars_date date,
        run_seconds double precision NOT NULL CHECK (run_seconds >= 0),
        start_count integer NOT NULL CHECK (start_count >= 0),
        after_filters_count integer NOT NULL CHECK (after_filters_count >= 0),
        after_indicator_conditions_count integer NOT NULL CHECK (after_indicator_conditions_count >= 0),
        result_count integer NOT NULL CHECK (result_count BETWEEN 0 AND 500),
        assistant_conversation_id bigint REFERENCES assistant_conversation (id) ON DELETE SET NULL
    );
    CREATE INDEX screen_result_screen_id_run_at_utc ON screen_result (screen_id, run_at_utc DESC);

    CREATE TABLE screen_result_row (
        screen_result_id bigint NOT NULL REFERENCES screen_result (id) ON DELETE CASCADE,
        position integer NOT NULL CHECK (position BETWEEN 1 AND 500),
        symbol text NOT NULL,
        exchange text NOT NULL,
        currency text NOT NULL,
        values jsonb NOT NULL,
        PRIMARY KEY (screen_result_id, position)
    );

    -- reason: the location of the condition that is not true, or "No value: <indicator>".
    CREATE TABLE screen_result_exclusion (
        screen_result_id bigint NOT NULL REFERENCES screen_result (id) ON DELETE CASCADE,
        symbol text NOT NULL,
        exchange text NOT NULL,
        currency text NOT NULL,
        reason text NOT NULL
    );
    CREATE INDEX screen_result_exclusion_screen_result_id ON screen_result_exclusion (screen_result_id);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE screen_result_exclusion, screen_result_row, screen_result, screen;")
