"""market_data: add the parameters to custom_indicator (issue #428)

Revision ID: d2f6b8a40c71
Revises: a9d3e7c15b42
"""

from alembic import op

revision = "d2f6b8a40c71"
down_revision = "a9d3e7c15b42"


def upgrade() -> None:
    op.execute("""
    -- The list of docs/architecture/indicator.md section 23.10.1: [{"name", "label", "value_type", "default",
    -- "minimum", "maximum", "description"}]. Each existing row has no parameters.
    ALTER TABLE custom_indicator ADD COLUMN parameters jsonb NOT NULL DEFAULT '[]';
    ALTER TABLE custom_indicator ALTER COLUMN parameters DROP DEFAULT;
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE custom_indicator DROP COLUMN parameters;")
