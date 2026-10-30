"""assistant: create the assistant_conversation table

Revision ID: 8d4b2e6f1a90
Revises: 8d4b1e7c2a90, 8d4b6f2a1c93, 8d4f2a6c1e93
"""

from alembic import op

revision = "8d4b2e6f1a90"
# This revision also joins the heads of market_data (#194), backtest (#165), and paper_trading (#214) into one head.
down_revision = ("8d4b1e7c2a90", "8d4b6f2a1c93", "8d4f2a6c1e93")


def upgrade() -> None:
    op.execute("""
    -- The metadata of each conversation with the AI assistant (docs/architecture/assistant.md 25.8.1).
    -- The messages are in one JSONL file of the assistant service for each conversation, not in PostgreSQL.
    -- title_state:
    --   new            the title is "New conversation" and the creation time. The title is generated after the first
    --                  answer.
    --   generating     the title generation runs.
    --   generated      the model wrote the title.
    --   not_generated  the title generation failed. ATrade does not try again.
    --   renamed        the user renamed the conversation. ATrade never changes the title again.
    -- A delete of the strategy deletes its conversations (ON DELETE CASCADE).
    CREATE TABLE assistant_conversation (
        id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        strategy_id bigint NOT NULL REFERENCES strategy (id) ON DELETE CASCADE,
        title text NOT NULL CHECK (char_length(title) BETWEEN 1 AND 200),
        title_state text NOT NULL DEFAULT 'new'
            CHECK (title_state IN ('new', 'generating', 'generated', 'not_generated', 'renamed')),
        created_at_utc timestamptz NOT NULL,
        last_provider text,
        last_model text,
        last_credential_name text
    );
    CREATE INDEX assistant_conversation_strategy_id ON assistant_conversation (strategy_id);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE assistant_conversation;")
