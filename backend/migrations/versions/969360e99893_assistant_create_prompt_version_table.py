"""assistant: create the assistant_prompt_version table and record the prompt of each conversation

Revision ID: 969360e99893
Revises: 8d4b2e6f1a90
"""

from alembic import op

revision = "969360e99893"
down_revision = "8d4b2e6f1a90"


def upgrade() -> None:
    op.execute("""
    -- The saved copies of the editable part of the system prompt (docs/architecture/assistant.md 25.9.1).
    -- A prompt version does not change after it is saved. The default text is in the code. ATrade saves it as
    -- version 1 when the first conversation starts or when the Prompt dialog first lists the versions.
    CREATE TABLE assistant_prompt_version (
        id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        version_number integer NOT NULL UNIQUE CHECK (version_number >= 1),
        text text NOT NULL CHECK (char_length(text) BETWEEN 1 AND 50000),
        created_at_utc timestamptz NOT NULL
    );

    CREATE FUNCTION assistant_prompt_version_refuse_update() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        RAISE EXCEPTION 'assistant_prompt_version rows are append-only. Save a new prompt version instead.';
    END;
    $$;

    CREATE TRIGGER assistant_prompt_version_append_only
        BEFORE UPDATE ON assistant_prompt_version
        FOR EACH ROW EXECUTE FUNCTION assistant_prompt_version_refuse_update();

    -- The conversations of #179 ran with the system prompt "You are the ATrade strategy assistant."
    -- They keep it as prompt version 1.
    INSERT INTO assistant_prompt_version (version_number, text, created_at_utc)
    SELECT 1, 'You are the ATrade strategy assistant.', now()
    WHERE EXISTS (SELECT 1 FROM assistant_conversation);

    -- prompt_version_id: the prompt version of the conversation. All runs of the conversation use it.
    -- fixed_prompt: the fixed part of the system prompt, made when the conversation started (the forbidden actions
    -- and the open strategy, the open version, and the last 3 backtests at that time).
    ALTER TABLE assistant_conversation
        ADD COLUMN prompt_version_id bigint REFERENCES assistant_prompt_version (id),
        ADD COLUMN fixed_prompt text NOT NULL DEFAULT '';
    UPDATE assistant_conversation
    SET prompt_version_id = (SELECT id FROM assistant_prompt_version WHERE version_number = 1);
    ALTER TABLE assistant_conversation
        ALTER COLUMN prompt_version_id SET NOT NULL,
        ALTER COLUMN fixed_prompt DROP DEFAULT;
    """)


def downgrade() -> None:
    op.execute("""
    ALTER TABLE assistant_conversation DROP COLUMN prompt_version_id, DROP COLUMN fixed_prompt;
    DROP TABLE assistant_prompt_version;
    DROP FUNCTION assistant_prompt_version_refuse_update();
    """)
