"""e2e data of the "Split check needed" state (docs/architecture/paper_trading.md section 11.11).

Each Playwright project gets its own instrument, because "Apply split 4:1" ends the state and the projects share one
database: IBKR shows 40 shares, the owner ledger has 10 shares of a stopped forward test, and the check found only the
position change (`position_only`, ratio 4). The e2e database is not cleared between runs, so each start of the e2e
server writes the state again.
"""

import hashlib
from datetime import UTC, datetime
from decimal import Decimal

import psycopg

from atrade.ibkr import PortfolioPosition
from tests.fakes.ibkr import make_stock_position

E2E_SPLIT_STRATEGY_NAME = "E2E split check"
E2E_SPLIT_STRATEGY_CODE = "# The strategy version of the e2e split check forward tests.\n"
E2E_SPLIT_LEDGER_QUANTITY = 10
E2E_SPLIT_ACCOUNT_QUANTITY = "40"
E2E_SPLIT_RATIO = 4
E2E_SPLIT_PRICE = "25"
E2E_SPLIT_CAPITAL_USD = Decimal(5000)
E2E_SPLIT_DAY_UTC = datetime(2026, 1, 2, tzinfo=UTC)


def make_split_symbol(project_name: str) -> str:
    """For example "SPCHRO" for the project chromium. frontend/e2e/stock_split.spec.ts uses the same rule."""
    return f"SP{project_name[:4].upper()}"


def find_split_forward_test_id(connection: psycopg.Connection, version_id: int, symbol: str) -> int:
    row = connection.execute(
        "SELECT id FROM forward_test WHERE strategy_version_id = %s AND symbol = %s", (version_id, symbol)
    ).fetchone()
    if row is not None:
        return int(row[0])
    row = connection.execute(
        """
        INSERT INTO forward_test (
            strategy_version_id, symbol, exchange, currency, bar_period, desired_state, status, allocated_capital_usd,
            created_at_utc, stopped_at_utc
        ) VALUES (%s, %s, 'NASDAQ', 'USD', '1-DAY', 'stopped', 'stopped', %s, %s, %s) RETURNING id
        """,
        (version_id, symbol, E2E_SPLIT_CAPITAL_USD, E2E_SPLIT_DAY_UTC, E2E_SPLIT_DAY_UTC),
    ).fetchone()
    assert row is not None
    return int(row[0])


def find_split_version_id(connection: psycopg.Connection) -> int:
    row = connection.execute(
        """
        SELECT strategy_version.id FROM strategy_version JOIN strategy ON strategy.id = strategy_version.strategy_id
        WHERE strategy.name = %s
        """,
        (E2E_SPLIT_STRATEGY_NAME,),
    ).fetchone()
    if row is not None:
        return int(row[0])
    strategy_row = connection.execute(
        "INSERT INTO strategy (name, created_at_utc) VALUES (%s, %s) RETURNING id",
        (E2E_SPLIT_STRATEGY_NAME, E2E_SPLIT_DAY_UTC),
    ).fetchone()
    assert strategy_row is not None
    version_row = connection.execute(
        """
        INSERT INTO strategy_version (strategy_id, version_number, code, code_sha256, created_at_utc)
        VALUES (%s, 1, %s, %s, %s) RETURNING id
        """,
        (
            strategy_row[0],
            E2E_SPLIT_STRATEGY_CODE,
            hashlib.sha256(E2E_SPLIT_STRATEGY_CODE.encode()).hexdigest(),
            E2E_SPLIT_DAY_UTC,
        ),
    ).fetchone()
    assert version_row is not None
    return int(version_row[0])


def add_split_checks(database_url: str, *, account: str, project_names: list[str]) -> list[PortfolioPosition]:
    """Writes the state for each project and returns the IBKR positions of the instruments. Call it after the owner
    ledger start, which deletes the ledger rows of the account."""
    symbols = [make_split_symbol(name) for name in project_names]
    with psycopg.connect(database_url) as connection:
        version_id = find_split_version_id(connection)
        connection.execute("DELETE FROM split_check WHERE account = %s", (account,))
        connection.execute("DELETE FROM stock_split WHERE symbol = ANY(%s)", (symbols,))
        for symbol in symbols:
            forward_test_id = find_split_forward_test_id(connection, version_id, symbol)
            connection.execute(
                """
                INSERT INTO owner_ledger_entry (
                    owner_kind, forward_test_id, entry_kind, time_utc, account, symbol, exchange, currency,
                    quantity_change, price, cash_change, ibkr_execution_id
                ) VALUES ('forward_test', %s, 'fill', %s, %s, %s, 'NASDAQ', 'USD', %s, 100, %s, %s)
                """,
                (
                    forward_test_id,
                    E2E_SPLIT_DAY_UTC,
                    account,
                    symbol,
                    E2E_SPLIT_LEDGER_QUANTITY,
                    -100 * E2E_SPLIT_LEDGER_QUANTITY,
                    f"e2e-split-{symbol}",
                ),
            )
            connection.execute(
                """
                INSERT INTO split_check (
                    account, symbol, exchange, currency, ex_date_utc, detected_ratio, evidence,
                    account_quantity_before, account_quantity_after, status, created_at_utc
                ) VALUES (%s, %s, 'NASDAQ', 'USD', %s, %s, 'position_only', %s, %s, 'needed', %s)
                """,
                (
                    account,
                    symbol,
                    E2E_SPLIT_DAY_UTC,
                    E2E_SPLIT_RATIO,
                    E2E_SPLIT_LEDGER_QUANTITY,
                    Decimal(E2E_SPLIT_ACCOUNT_QUANTITY),
                    E2E_SPLIT_DAY_UTC,
                ),
            )
        connection.commit()
    return [
        make_stock_position(account, symbol=symbol, quantity=E2E_SPLIT_ACCOUNT_QUANTITY, market_price=E2E_SPLIT_PRICE)
        for symbol in symbols
    ]
