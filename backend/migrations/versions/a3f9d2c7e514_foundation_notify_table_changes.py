"""foundation: notify the table changes that the /ws/ change sockets push

Revision ID: a3f9d2c7e514
Revises: e2b3fdd9c1ee
"""

from alembic import op

revision = "a3f9d2c7e514"
down_revision = "e2b3fdd9c1ee"

# The tables that the change sockets watch (docs/architecture.md section 13, "Live updates"). Each writer changes
# them: the Web process, the backtest child process, the forward-test worker, and the assistant port.
WATCHED_TABLES = (
    "backtest",
    "parameter_sweep",
    "strategy",
    "strategy_version",
    "screen",
    "screen_result",
    "watchlist_instrument",
    "forward_test",
    "forward_test_interruption",
    "forward_test_equity_point",
    "forward_test_fill",
    "forward_test_same_period_backtest",
)


def upgrade() -> None:
    op.execute("""
    -- One notification for each changing statement, with the table name as payload. PostgreSQL sends it at the
    -- commit and sends equal notifications of one transaction only once.
    CREATE FUNCTION notify_table_change() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        RETURN NULL;
    END;
    $$;
    """)
    for table in WATCHED_TABLES:
        op.execute(f"""
        CREATE TRIGGER notify_table_change AFTER INSERT OR UPDATE OR DELETE OR TRUNCATE ON {table}
        FOR EACH STATEMENT EXECUTE FUNCTION notify_table_change();
        """)


def downgrade() -> None:
    for table in WATCHED_TABLES:
        op.execute(f"DROP TRIGGER notify_table_change ON {table};")
    op.execute("DROP FUNCTION notify_table_change();")
