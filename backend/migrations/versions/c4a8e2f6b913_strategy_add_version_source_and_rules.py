"""strategy: add the source and rules columns to strategy_version

Revision ID: c4a8e2f6b913
Revises: 8d4f2a6c1e93
"""

from alembic import op

revision = "c4a8e2f6b913"
down_revision = "8d4f2a6c1e93"


def upgrade() -> None:
    op.execute("""
    -- The version source and the rules of the rule builder (docs/architecture/strategy.md section 9.1.1).
    -- The DEFAULT fills the existing rows and stays. An UPDATE would hit the trigger strategy_version_append_only,
    -- which refuses each UPDATE of strategy_version, also of rules.
    -- A named CHECK constraint holds the source values. Phase 2 drops it and adds it again with ai_assistant.
    ALTER TABLE strategy_version
        ADD COLUMN source text NOT NULL DEFAULT 'user'
            CONSTRAINT strategy_version_source_check CHECK (source IN ('user', 'rule_builder')),
        ADD COLUMN rules jsonb;
    """)


def downgrade() -> None:
    op.execute("""
    ALTER TABLE strategy_version DROP COLUMN rules, DROP COLUMN source;
    """)
