"""market_data: create the custom indicators of docs/architecture/indicator.md section 23.10

Revision ID: b7e4c2a19d36
Revises: f2a6d9c41e73
"""

from alembic import op

revision = "b7e4c2a19d36"
down_revision = "f2a6d9c41e73"


def upgrade() -> None:
    op.execute("""
    -- A stored indicator reference holds the expression (ADR 0009), so a delete of a row changes no saved reference. The
    -- identity never gives a deleted id again, so the catalog key `custom_<id>` of a row is never used 2 times.
    CREATE TABLE custom_indicator (
        custom_indicator_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        name text NOT NULL,
        expression text NOT NULL,
        chart_placement text NOT NULL CHECK (chart_placement IN ('price', 'own')),
        value_description text NOT NULL,
        created_at_utc timestamptz NOT NULL,
        changed_at_utc timestamptz NOT NULL
    );

    CREATE UNIQUE INDEX custom_indicator_name ON custom_indicator (lower(name));
    """)


def downgrade() -> None:
    op.execute("DROP TABLE custom_indicator;")
