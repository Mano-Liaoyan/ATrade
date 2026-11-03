"""market_data: create the chart indicator set of docs/architecture/indicator.md section 23.9.7

Revision ID: e5c3a7f1b2d9
Revises: c4a81e6d2b07
"""

from alembic import op

revision = "e5c3a7f1b2d9"
down_revision = "c4a81e6d2b07"


def upgrade() -> None:
    op.execute("""
    -- The indicators of the instrument page chart and the favorites of "Add indicator": 1 row. The last save wins.
    CREATE TABLE chart_indicator_set (
        single_row boolean PRIMARY KEY DEFAULT true CHECK (single_row),
        panes jsonb NOT NULL,
        favorites jsonb NOT NULL,
        changed_at_utc timestamptz NOT NULL
    );

    INSERT INTO chart_indicator_set (panes, favorites, changed_at_utc)
    VALUES ('[{"indicators": []}]', '[]', now());
    """)


def downgrade() -> None:
    op.execute("DROP TABLE chart_indicator_set;")
