"""strategy: add the source ai_assistant, strategy_version.conversation_id, and the discarded mark

Revision ID: 2f7a9c3e5b14
Revises: 8d4b2e6f1a90
"""

from alembic import op

revision = "2f7a9c3e5b14"
# Follows the assistant_conversation table (#179). The source column of #171 is earlier in the chain.
down_revision = "8d4b2e6f1a90"


def upgrade() -> None:
    op.execute("""
    -- The versions that the AI assistant saved (docs/architecture/assistant.md 25.5.1, strategy.md 9.1.1).
    -- Only a version with the source ai_assistant has a conversation. A delete of the conversation sets it to null.
    ALTER TABLE strategy_version
        DROP CONSTRAINT strategy_version_source_check,
        ADD CONSTRAINT strategy_version_source_check CHECK (source IN ('user', 'rule_builder', 'ai_assistant')),
        ADD COLUMN conversation_id bigint REFERENCES assistant_conversation (id) ON DELETE SET NULL,
        ADD CONSTRAINT strategy_version_conversation_check CHECK (conversation_id IS NULL OR source = 'ai_assistant');

    -- The discarded mark. A row here marks the version as discarded. The version row itself does not change,
    -- because strategy_version is append-only. A delete of the version (strategy delete) deletes the mark.
    CREATE TABLE strategy_version_discard (
        strategy_version_id bigint PRIMARY KEY REFERENCES strategy_version (id) ON DELETE CASCADE,
        discarded_at_utc timestamptz NOT NULL
    );

    -- The trigger strategy_version_append_only still refuses each UPDATE statement. It lets through only the
    -- ON DELETE SET NULL of conversation_id: PostgreSQL runs it inside the foreign key trigger, so the trigger depth
    -- is more than 1, and it changes no other column.
    CREATE OR REPLACE FUNCTION strategy_version_refuse_update() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        IF pg_trigger_depth() > 1
            AND OLD.conversation_id IS NOT NULL
            AND NEW.conversation_id IS NULL
            AND (to_jsonb(NEW) - 'conversation_id') = (to_jsonb(OLD) - 'conversation_id') THEN
            RETURN NEW;
        END IF;
        RAISE EXCEPTION 'strategy_version rows are append-only. Save a new version instead.';
    END;
    $$;
    """)


def downgrade() -> None:
    op.execute("""
    CREATE OR REPLACE FUNCTION strategy_version_refuse_update() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        RAISE EXCEPTION 'strategy_version rows are append-only. Save a new version instead.';
    END;
    $$;
    DROP TABLE strategy_version_discard;
    ALTER TABLE strategy_version
        DROP CONSTRAINT strategy_version_conversation_check,
        DROP COLUMN conversation_id,
        DROP CONSTRAINT strategy_version_source_check,
        ADD CONSTRAINT strategy_version_source_check CHECK (source IN ('user', 'rule_builder'));
    """)
