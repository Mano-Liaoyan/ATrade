"""The platform DataActor that saves the bars and records the equity of a forward test
(docs/architecture/forward_test.md section 12.8).

The actor runs in the NautilusTrader backtest engine with the bar count test strategy and a small bar file. The fills
come from the owner ledger, where the ATrade execution client writes them. The test asserts the exact rows of the bar
and record tables in a real PostgreSQL.
"""

import csv
import hashlib
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import LiteralString

import httpx
import psycopg
import pytest
from nautilus_trader.model import BarType
from nautilus_trader.persistence import BarDataWrangler

from atrade.backtest.arrow_bars import convert_bars_to_arrow_bytes
from atrade.backtest.strategy_engine_run import create_engine, create_instrument
from atrade.forward_test import ForwardTestRecorder, RecorderInput
from atrade.foundation.bar import Bar, BarPeriod
from atrade.foundation.instrument import Instrument
from atrade.strategy import load_strategy_classes
from tests.backtest.real_runner import run_backtest_runner, wait_for_final_status
from tests.fakes.clock import FixedClock

TEST_DIRECTORY = Path(__file__).parents[1] / "backtest"
TEST_STRATEGY_FILE = TEST_DIRECTORY / "strategies" / "buy_and_sell_by_bar_count.py"
TEST_BAR_FILE = TEST_DIRECTORY / "bars" / "btest_arca_usd_1_day.csv"
BAR_COUNT = 10
START_BALANCE_USD = Decimal(10000)
DAY_BAR_PERIOD = BarPeriod("1-DAY")
INSTRUMENT = Instrument(symbol="BTEST", exchange="ARCA", currency="USD")


def read_test_bars() -> list[Bar]:
    with TEST_BAR_FILE.open() as bar_file:
        rows = list(csv.DictReader(bar_file))[:BAR_COUNT]
    return [
        Bar(
            start_utc=datetime.fromisoformat(row["start_utc"]),
            open=Decimal(row["open"]),
            high=Decimal(row["high"]),
            low=Decimal(row["low"]),
            close=Decimal(row["close"]),
            volume=Decimal(row["volume"]),
        )
        for row in rows
    ]


def insert_forward_test(database_url: str) -> int:
    code = TEST_STRATEGY_FILE.read_text()
    with psycopg.connect(database_url, autocommit=True) as connection:
        now_utc = datetime(2026, 3, 1, tzinfo=UTC)
        strategy_row = connection.execute(
            "INSERT INTO strategy (name, created_at_utc) VALUES ('Bar count', %(now)s) RETURNING id", {"now": now_utc}
        ).fetchone()
        assert strategy_row is not None
        version_row = connection.execute(
            """
            INSERT INTO strategy_version (strategy_id, version_number, code, code_sha256, created_at_utc)
            VALUES (%(strategy_id)s, 1, %(code)s, %(code_sha256)s, %(now)s) RETURNING id
            """,
            {
                "strategy_id": strategy_row[0],
                "code": code,
                "code_sha256": hashlib.sha256(code.encode()).hexdigest(),
                "now": now_utc,
            },
        ).fetchone()
        assert version_row is not None
        forward_test_row = connection.execute(
            """
            INSERT INTO forward_test (strategy_version_id, symbol, exchange, currency, bar_period, desired_state,
                status, client_id, allocated_capital_usd, created_at_utc)
            VALUES (%(version_id)s, 'BTEST', 'ARCA', 'USD', '1-DAY', 'running', 'running', 10, 10000, %(now)s)
            RETURNING id
            """,
            {"version_id": version_row[0], "now": now_utc},
        ).fetchone()
        assert forward_test_row is not None
        return int(forward_test_row[0])


def insert_ledger_fills(database_url: str, forward_test_id: int) -> None:
    """The ATrade execution client wrote 2 fills: a buy of 10 at 104 and a sell of 10 at 106, and a fill of another
    forward test."""
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.cursor().executemany(
            """
            INSERT INTO owner_ledger_entry (owner_kind, forward_test_id, entry_kind, time_utc, account, symbol,
                exchange, currency, quantity_change, price, cash_change, ibkr_execution_id, ibkr_order_id)
            VALUES ('forward_test', %s, 'fill', %s, 'DU1234567', 'BTEST', 'ARCA', 'USD', %s, %s, %s, %s, 1)
            """,
            [
                (forward_test_id, make_time(5), 10, 104, -1040, "e1"),
                (forward_test_id, make_time(10), -10, 106, 1060, "e2"),
                (forward_test_id + 1, make_time(5), 50, 104, -5200, "e3"),
            ],
        )


def run_engine_with_recorder(
    *, database_url: str, forward_test_id: int, work_directory: Path, instrument: Instrument = INSTRUMENT
) -> None:
    bars = read_test_bars()
    nautilus_instrument = create_instrument(INSTRUMENT, bars)
    bar_type = BarType.from_str(f"{nautilus_instrument.id}-{DAY_BAR_PERIOD.value}-LAST-EXTERNAL")
    wrangler = BarDataWrangler(str(bar_type), nautilus_instrument.price_precision, 0)
    nautilus_bars = wrangler.process_record_batch_bytes(convert_bars_to_arrow_bytes(bars, DAY_BAR_PERIOD))
    engine = create_engine(
        starting_cash=START_BALANCE_USD, currency="USD", venue=nautilus_instrument.venue, work_directory=work_directory
    )
    engine.add_instrument(nautilus_instrument)
    engine.add_data(nautilus_bars)
    strategy_class, config_class = load_strategy_classes(TEST_STRATEGY_FILE.read_text(), work_directory)
    config = config_class(instrument_id=nautilus_instrument.id, bar_type=bar_type)  # pyright: ignore[reportCallIssue]
    engine.add_strategy(strategy_class(config))
    engine.add_actor(
        ForwardTestRecorder(
            RecorderInput(
                database_url=database_url,
                forward_test_id=forward_test_id,
                instrument=instrument,
                instrument_id=nautilus_instrument.id,
                bar_type=bar_type,
                bar_period=DAY_BAR_PERIOD,
                start_balance_usd=START_BALANCE_USD,
            )
        )
    )
    engine.run()
    engine.dispose()


def read_table_rows(database_url: str, query: LiteralString) -> list[tuple[object, ...]]:
    with psycopg.connect(database_url) as connection:
        return connection.execute(query).fetchall()


def make_time(day: int) -> datetime:
    return datetime(2026, 3, day, tzinfo=UTC)


def test_records_each_new_fill_once_and_one_equity_point_at_the_end_of_each_bar(
    database_url: str, tmp_path: Path
) -> None:
    forward_test_id = insert_forward_test(database_url)
    insert_ledger_fills(database_url, forward_test_id)

    run_engine_with_recorder(database_url=database_url, forward_test_id=forward_test_id, work_directory=tmp_path)

    # The recorder writes no fill: the owner ledger has them (section 12.8).
    assert read_table_rows(database_url, "SELECT count(*) FROM forward_test_fill") == [(0,)]
    equity_points = read_table_rows(
        database_url, "SELECT time_utc, equity_usd FROM forward_test_equity_point ORDER BY time_utc"
    )
    # The allocated capital 10000 - 10 * 104 = 8960 cash, plus 10 shares at the close. The fill of the other forward
    # test does not count.
    assert equity_points == [
        (make_time(3), Decimal(10000)),
        (make_time(4), Decimal(10000)),
        (make_time(5), Decimal(10000)),
        (make_time(6), Decimal(10020)),
        (make_time(7), Decimal(10040)),
        (make_time(8), Decimal(10060)),
        (make_time(9), Decimal(10040)),
        (make_time(10), Decimal(10020)),
        (make_time(11), Decimal(10020)),
        (make_time(12), Decimal(10020)),
    ]


def test_a_second_run_over_the_same_bars_adds_no_row(database_url: str, tmp_path: Path) -> None:
    forward_test_id = insert_forward_test(database_url)
    run_engine_with_recorder(database_url=database_url, forward_test_id=forward_test_id, work_directory=tmp_path)

    # A restart gets the same bars again (section 12.7).
    run_engine_with_recorder(database_url=database_url, forward_test_id=forward_test_id, work_directory=tmp_path)

    assert read_table_rows(database_url, "SELECT count(*) FROM forward_test_equity_point") == [(BAR_COUNT,)]
    assert read_table_rows(database_url, "SELECT count(*) FROM bar") == [(BAR_COUNT,)]


def test_saves_each_bar_in_the_bar_store_with_its_saved_range(database_url: str, tmp_path: Path) -> None:
    forward_test_id = insert_forward_test(database_url)

    run_engine_with_recorder(database_url=database_url, forward_test_id=forward_test_id, work_directory=tmp_path)

    saved_bars = read_table_rows(
        database_url,
        """
        SELECT symbol, exchange, currency, bar_period, start_utc, open, high, low, close, volume FROM bar
        ORDER BY start_utc
        """,
    )
    assert saved_bars == [
        ("BTEST", "ARCA", "USD", "1-DAY", bar.start_utc, bar.open, bar.high, bar.low, bar.close, bar.volume)
        for bar in read_test_bars()
    ]
    # The bar ranges touch, so the store joins them into one saved range.
    assert read_table_rows(database_url, "SELECT symbol, bar_period, start_utc, end_utc FROM bar_saved_range") == [
        ("BTEST", "1-DAY", make_time(2), make_time(12))
    ]


def test_a_failed_bar_save_does_not_stop_the_records(database_url: str, tmp_path: Path) -> None:
    forward_test_id = insert_forward_test(database_url)
    # PostgreSQL refuses a NUL character in a text column, so each bar save fails.
    instrument_that_cannot_be_saved = Instrument(symbol="BTEST\x00", exchange="ARCA", currency="USD")

    run_engine_with_recorder(
        database_url=database_url,
        forward_test_id=forward_test_id,
        work_directory=tmp_path,
        instrument=instrument_that_cannot_be_saved,
    )

    assert read_table_rows(database_url, "SELECT count(*) FROM bar") == [(0,)]
    assert read_table_rows(database_url, "SELECT count(*) FROM forward_test_equity_point") == [(BAR_COUNT,)]


@pytest.mark.anyio
async def test_a_same_period_backtest_runs_on_the_bars_that_the_forward_test_saved(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock, tmp_path: Path
) -> None:
    forward_test_id = insert_forward_test(database_url)
    run_engine_with_recorder(database_url=database_url, forward_test_id=forward_test_id, work_directory=tmp_path)
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            """
            UPDATE forward_test SET status = 'stopped', desired_state = 'stopped', client_id = NULL,
                stopped_at_utc = %(stopped_at_utc)s
            WHERE id = %(id)s
            """,
            {"id": forward_test_id, "stopped_at_utc": make_time(12)},
        )

    response = await web_client.post(f"/api/forward-tests/{forward_test_id}/same-period-backtests")
    assert response.status_code == 201
    async with run_backtest_runner(web_client, database_url, clock, timeout_seconds=60):
        backtest = await wait_for_final_status(web_client, response.json()["backtest_id"])

    assert backtest["status"] == "finished", backtest["error_message"]
    assert (backtest["start_utc"], backtest["end_utc"]) == ("2026-03-01T00:00:00Z", "2026-03-12T00:00:00Z")
    # The same bars give the same 2 trades as the forward test records.
    assert [(trade["time_utc"], trade["side"]) for trade in backtest["trades"]] == [
        ("2026-03-05T00:00:00Z", "BUY"),
        ("2026-03-10T00:00:00Z", "SELL"),
    ]
