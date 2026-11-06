"""market_data: add kept and the conversation to custom_indicator, and its change trigger (issue #374)

Revision ID: e5c7a1f4b92d
Revises: b7e4c2a19d36
"""

from alembic import op

revision = "e5c7a1f4b92d"
down_revision = "b7e4c2a19d36"


def upgrade() -> None:
    op.execute("""
    -- The rule of a screen (docs/architecture/screen.md section 24.8): assistant_conversation_id is null for an indicator
    -- of the user. A delete of the conversation keeps the indicator. Each existing row is an indicator of the user.
    ALTER TABLE custom_indicator
        ADD COLUMN kept boolean NOT NULL DEFAULT true,
        ADD COLUMN assistant_conversation_id bigint REFERENCES assistant_conversation (id) ON DELETE SET NULL;
    ALTER TABLE custom_indicator ALTER COLUMN kept DROP DEFAULT;

    -- The AI assistant writes through port 8001, so the Settings page gets the change from /ws/custom-indicators.
    CREATE TRIGGER notify_table_change AFTER INSERT OR UPDATE OR DELETE OR TRUNCATE ON custom_indicator
    FOR EACH STATEMENT EXECUTE FUNCTION notify_table_change();
    """)


def downgrade() -> None:
    op.execute("""
    DROP TRIGGER notify_table_change ON custom_indicator;
    ALTER TABLE custom_indicator DROP COLUMN kept, DROP COLUMN assistant_conversation_id;
    """)
