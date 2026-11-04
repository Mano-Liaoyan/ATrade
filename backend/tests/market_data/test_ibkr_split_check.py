"""The IBKR stock split check program after the Databento import: pacing violations, lost connections, a new run after
a stop, and the reads of a second import.

Real PostgreSQL, hand-made DBN files of the Databento fake, and the IBKR fake (docs/architecture/market_data.md
section 8.8.3).
"""

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import psycopg
import pytest

from atrade.foundation.bar import BarPeriod, TimeRange
from atrade.foundation.instrument import Instrument
from atrade.market_data import has_pending_split_check, import_databento_files, run_ibkr_split_check
from tests.fakes.clock import FixedClock
from tests.fakes.databento import write_dbn_files
from tests.fakes.ibkr import FakeGatewayConnection, HistoricalBarRequest
from tests.market_data.test_stock_split_import import (
    STOCK_SPLIT_QUERY,
    TRADING_DAYS,
    DailyBar,
    create_bars,
    create_history_files,
    ibkr_bars,
    read_bars,
    read_table,
    serve_same_closes,
    utc_day,
)

CHECK_TIME_UTC = datetime(2026, 11, 3, 12, 0, tzinfo=UTC)
SPLT = Instrument(symbol="SPLT", exchange="NASDAQ", currency="USD")
STAY = Instrument(symbol="STAY", exchange="NASDAQ", currency="USD")
PACING_MESSAGE = (
    "Error 162, reqId 7: Historical Market Data Service error message:Historical data request pacing violation"
)
NO_ANSWER_MESSAGE = "IB Gateway did not answer the historical data request in time."
NO_CONTRACT_MESSAGE = "Error 200, reqId 3: No security definition has been found for the request"
SPLIT_CHECK_QUERY = (
    "SELECT symbol, check_end_utc, checked_end_utc, checked_at_utc FROM ibkr_split_check ORDER BY symbol"
)


class StopCheckError(Exception):
    """Stops the check program in a test, like a stop of its container."""


class WaitRecorder:
    """Records each wait of the check program and does not wait. `on_wait` changes the fakes during a wait."""

    def __init__(self, on_wait: Callable[[float], None] | None = None) -> None:
        self.seconds: list[float] = []
        self.on_wait = on_wait

    async def wait(self, seconds: float) -> None:
        self.seconds.append(seconds)
        if self.on_wait is not None:
            self.on_wait(seconds)

    def read_long_waits(self) -> list[float]:
        """The waits after a pacing violation or a lost connection, without the wait after each instrument."""
        return [seconds for seconds in self.seconds if seconds > 1]


@pytest.fixture
async def gateway() -> FakeGatewayConnection:
    connection = FakeGatewayConnection(managed_accounts=["DU1234567"])
    await connection.connect()
    return connection


def split_bars() -> list[DailyBar]:
    """A 2-for-1 split on 2020-01-08. Databento has the prices that are not adjusted."""
    return create_bars(
        "SPLT",
        TRADING_DAYS[:4],
        [("200", "202", 1000), ("202", "204", 1100), ("102", "103", 2400), ("103", "104", 2300)],
    )


def serve_split_closes(gateway: FakeGatewayConnection) -> None:
    gateway.historical_bars[SPLT] = ibkr_bars(TRADING_DAYS[:4], ["101.05", "102.10", "103.00", "104.00"])


def import_bars(database_url: str, directory: Path, bars: list[DailyBar]) -> None:
    import_databento_files(
        database_url=database_url,
        file_paths=write_dbn_files(directory, create_history_files(bars)),
        still_trading_rule="ibkr_check",
    )


async def run_check(database_url: str, gateway: FakeGatewayConnection, recorder: WaitRecorder) -> None:
    await run_ibkr_split_check(
        database_url=database_url, gateway=gateway, clock=FixedClock(CHECK_TIME_UTC), wait=recorder.wait
    )


async def assert_split_applied(database_url: str) -> None:
    assert read_table(database_url, STOCK_SPLIT_QUERY) == [
        ("SPLT", "NASDAQ", "USD", utc_day(TRADING_DAYS[2]), Decimal(2), "databento_import", "bar_evidence")
    ]
    bars = await read_bars(database_url, "SPLT")
    assert [(bar.close, bar.volume) for bar in bars] == [
        (Decimal(101), Decimal(2000)),
        (Decimal(102), Decimal(2200)),
        (Decimal(103), Decimal(2400)),
        (Decimal(104), Decimal(2300)),
    ]


@pytest.mark.anyio
async def test_the_import_does_not_adjust_an_instrument_that_still_trades_before_the_check(
    database_url: str, tmp_path: Path, gateway: FakeGatewayConnection
) -> None:
    import_bars(database_url, tmp_path, split_bars())

    assert read_table(database_url, STOCK_SPLIT_QUERY) == []
    assert [bar.close for bar in await read_bars(database_url, "SPLT")] == [
        Decimal(202),
        Decimal(204),
        Decimal(103),
        Decimal(104),
    ]
    assert read_table(database_url, SPLIT_CHECK_QUERY) == [("SPLT", utc_day(TRADING_DAYS[4]), None, None)]
    assert gateway.historical_bar_requests == []


@pytest.mark.anyio
async def test_the_check_adjusts_the_stored_bars_and_records_the_checked_end(
    database_url: str, tmp_path: Path, gateway: FakeGatewayConnection
) -> None:
    import_bars(database_url, tmp_path, split_bars())
    serve_split_closes(gateway)

    await run_check(database_url, gateway, WaitRecorder())

    await assert_split_applied(database_url)
    assert read_table(database_url, SPLIT_CHECK_QUERY) == [
        ("SPLT", utc_day(TRADING_DAYS[4]), utc_day(TRADING_DAYS[4]), CHECK_TIME_UTC)
    ]
    assert gateway.historical_bar_requests == [
        HistoricalBarRequest(SPLT, BarPeriod.ONE_DAY, TimeRange(utc_day(TRADING_DAYS[0]), utc_day(TRADING_DAYS[4])))
    ]


@pytest.mark.anyio
async def test_after_a_pacing_violation_the_check_waits_longer_each_time_and_then_continues(
    database_url: str, tmp_path: Path, gateway: FakeGatewayConnection
) -> None:
    import_bars(database_url, tmp_path, split_bars())
    serve_split_closes(gateway)
    gateway.next_historical_bars_errors = [PACING_MESSAGE, PACING_MESSAGE]
    recorder = WaitRecorder()

    await run_check(database_url, gateway, recorder)

    assert recorder.read_long_waits() == [60.0, 120.0]
    assert len(gateway.historical_bar_requests) == 3
    await assert_split_applied(database_url)


@pytest.mark.anyio
async def test_after_a_lost_gateway_connection_the_check_connects_again_and_continues(
    database_url: str, tmp_path: Path, gateway: FakeGatewayConnection
) -> None:
    import_bars(database_url, tmp_path, split_bars())
    serve_split_closes(gateway)
    gateway.is_gateway_reachable = False
    gateway.connected = False

    def start_gateway(_seconds: float) -> None:
        gateway.is_gateway_reachable = True

    recorder = WaitRecorder(start_gateway)

    await run_check(database_url, gateway, recorder)

    assert recorder.read_long_waits() == [60.0]
    assert gateway.connected
    await assert_split_applied(database_url)


@pytest.mark.anyio
async def test_after_a_lost_ibkr_link_the_check_tries_the_instrument_again(
    database_url: str, tmp_path: Path, gateway: FakeGatewayConnection
) -> None:
    """The API connection stays, but IB Gateway has no connection to the IBKR servers. The request is not a sign that
    IBKR has no bars of the instrument."""
    import_bars(database_url, tmp_path, split_bars())
    serve_split_closes(gateway)
    gateway.next_historical_bars_errors = [NO_ANSWER_MESSAGE]
    gateway.has_ibkr_connection = False

    def restore_ibkr_link(_seconds: float) -> None:
        gateway.has_ibkr_connection = True

    recorder = WaitRecorder(restore_ibkr_link)

    await run_check(database_url, gateway, recorder)

    assert recorder.read_long_waits() == [60.0]
    await assert_split_applied(database_url)


@pytest.mark.anyio
async def test_a_new_run_after_a_stop_checks_only_the_instruments_that_still_wait(
    database_url: str, tmp_path: Path, gateway: FakeGatewayConnection
) -> None:
    stay_bars = create_bars("STAY", TRADING_DAYS[:4], [("50", "51", 1000)] * 4)
    import_bars(database_url, tmp_path, [*split_bars(), *stay_bars])
    serve_split_closes(gateway)
    serve_same_closes(gateway, stay_bars)

    def stop_at_the_second_instrument(seconds: float) -> None:
        if seconds > 1:
            raise StopCheckError
        gateway.next_historical_bars_errors = [PACING_MESSAGE]

    with pytest.raises(StopCheckError):
        await run_check(database_url, gateway, WaitRecorder(stop_at_the_second_instrument))
    checked = [row[0] for row in read_table(database_url, SPLIT_CHECK_QUERY) if row[2] is not None]
    gateway.historical_bar_requests.clear()

    await run_check(database_url, gateway, WaitRecorder())

    assert checked == ["SPLT"]
    assert [request.instrument for request in gateway.historical_bar_requests] == [STAY]
    assert all(row[2] is not None for row in read_table(database_url, SPLIT_CHECK_QUERY))
    await assert_split_applied(database_url)


@pytest.mark.anyio
async def test_a_second_import_of_the_same_daily_bars_needs_no_ibkr_read(
    database_url: str, tmp_path: Path, gateway: FakeGatewayConnection
) -> None:
    import_bars(database_url, tmp_path, split_bars())
    serve_split_closes(gateway)
    await run_check(database_url, gateway, WaitRecorder())
    gateway.historical_bar_requests.clear()

    import_bars(database_url, tmp_path / "again", split_bars())
    await run_check(database_url, gateway, WaitRecorder())

    assert gateway.historical_bar_requests == []
    await assert_split_applied(database_url)


def weekdays(first: date, last: date) -> list[date]:
    days = [first + timedelta(days=offset) for offset in range((last - first).days + 1)]
    return [day for day in days if day.weekday() < 5]


@pytest.mark.anyio
async def test_an_import_of_new_days_reads_only_the_new_days_and_some_checked_days(
    database_url: str, tmp_path: Path, gateway: FakeGatewayConnection
) -> None:
    first_days = weekdays(date(2020, 1, 6), date(2020, 1, 31))
    all_days = weekdays(date(2020, 1, 6), date(2020, 2, 14))
    all_bars = create_bars("STAY", all_days, [("50", "51", 1000)] * len(all_days))
    serve_same_closes(gateway, all_bars)
    import_bars(database_url, tmp_path, all_bars[: len(first_days)])
    await run_check(database_url, gateway, WaitRecorder())
    gateway.historical_bar_requests.clear()

    import_bars(database_url, tmp_path / "later", all_bars)
    await run_check(database_url, gateway, WaitRecorder())

    # The checked end is 2020-02-01. The check reads again from 10 days before it: the first weekday is 2020-01-22.
    assert gateway.historical_bar_requests == [
        HistoricalBarRequest(STAY, BarPeriod.ONE_DAY, TimeRange(utc_day(date(2020, 1, 22)), utc_day(date(2020, 2, 15))))
    ]


@pytest.mark.anyio
async def test_after_3_timeouts_of_the_same_instrument_the_check_uses_the_detection_rule_and_continues(
    database_url: str, tmp_path: Path, gateway: FakeGatewayConnection
) -> None:
    """IBKR gives no answer for 1 instrument. After each timeout, the gateway marks the IBKR link as lost, so the
    timeout looks like a lost link. The check does not try the instrument again without end."""
    import_bars(database_url, tmp_path, split_bars())
    gateway.next_historical_bars_errors = [NO_ANSWER_MESSAGE] * 3
    gateway.has_ibkr_connection = False
    recorder = WaitRecorder()

    await run_check(database_url, gateway, recorder)

    assert recorder.read_long_waits() == [60.0, 60.0]
    assert len(gateway.historical_bar_requests) == 3
    assert read_table(database_url, STOCK_SPLIT_QUERY) == [
        ("SPLT", "NASDAQ", "USD", utc_day(TRADING_DAYS[2]), Decimal(2), "databento_import", None)
    ]
    assert [row[2] for row in read_table(database_url, SPLIT_CHECK_QUERY)] == [utc_day(TRADING_DAYS[4])]


@pytest.mark.anyio
async def test_closes_that_differ_by_some_percent_on_single_days_are_not_a_stock_split(
    database_url: str, tmp_path: Path, gateway: FakeGatewayConnection
) -> None:
    """A stock with few trades: the official close and the IBKR close differ by about 5% on some days. Each such day
    changes the close ratio by more than 3%, but the ratio does not stay at a new level."""
    closes = ["100", "105", "100", "95", "100", "106"]
    bars = create_bars("SPLT", TRADING_DAYS, [(close, close, 1000) for close in closes])
    import_bars(database_url, tmp_path, bars)
    gateway.historical_bars[SPLT] = ibkr_bars(TRADING_DAYS, ["100"] * len(TRADING_DAYS))

    await run_check(database_url, gateway, WaitRecorder())

    assert read_table(database_url, STOCK_SPLIT_QUERY) == []
    assert [bar.close for bar in await read_bars(database_url, "SPLT")] == [Decimal(close) for close in closes]
    assert [row[2] for row in read_table(database_url, SPLIT_CHECK_QUERY)] == [
        utc_day(TRADING_DAYS[-1]) + timedelta(days=1)
    ]


@pytest.mark.anyio
async def test_a_reverse_split_of_1_for_150_gets_the_split_ratio_1_150(
    database_url: str, tmp_path: Path, gateway: FakeGatewayConnection
) -> None:
    """A split ratio below 1/50 was rounded to 0 before, and the database refused the stock split."""
    bars = create_bars(
        "SPLT",
        TRADING_DAYS[:4],
        [("1.00", "1.00", 150000), ("1.00", "1.01", 150000), ("150", "150", 1000), ("150", "151", 1000)],
    )
    import_bars(database_url, tmp_path, bars)
    gateway.historical_bars[SPLT] = ibkr_bars(TRADING_DAYS[:4], ["150", "151.5", "150", "151"])

    await run_check(database_url, gateway, WaitRecorder())

    assert read_table(database_url, STOCK_SPLIT_QUERY) == [
        (
            "SPLT",
            "NASDAQ",
            "USD",
            utc_day(TRADING_DAYS[2]),
            Decimal(1) / Decimal(150),
            "databento_import",
            "bar_evidence",
        )
    ]
    # The split ratio 1/150 has no exact decimal form, so the adjusted closes differ in the last of 28 digits.
    assert [round(bar.close, 6) for bar in await read_bars(database_url, "SPLT")] == [
        Decimal(150),
        Decimal("151.5"),
        Decimal(150),
        Decimal(151),
    ]


@pytest.mark.anyio
async def test_without_ibkr_bars_the_detection_rule_finds_the_stock_split_and_it_waits_for_the_user_check(
    database_url: str, tmp_path: Path, gateway: FakeGatewayConnection
) -> None:
    """IBKR does not know the contract. The close of 80 then the next open of 40 is a ratio of 2, and the volume goes
    up. The bars do not change until the user confirms the stock split."""
    bars = create_bars(
        "SPLT", TRADING_DAYS[:4], [("79", "80", 1000), ("80", "80", 1000), ("40", "41", 2100), ("41", "42", 2000)]
    )
    import_bars(database_url, tmp_path, bars)
    gateway.historical_bars_error_message = NO_CONTRACT_MESSAGE

    await run_check(database_url, gateway, WaitRecorder())

    assert read_table(database_url, STOCK_SPLIT_QUERY) == [
        ("SPLT", "NASDAQ", "USD", utc_day(TRADING_DAYS[2]), Decimal(2), "databento_import", None)
    ]
    assert [bar.close for bar in await read_bars(database_url, "SPLT")] == [
        Decimal(80),
        Decimal(80),
        Decimal(41),
        Decimal(42),
    ]
    assert [row[2] for row in read_table(database_url, SPLIT_CHECK_QUERY)] == [utc_day(TRADING_DAYS[4])]


async def read_pending(database_url: str, instrument: Instrument | None, currency: str) -> bool:
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        return await has_pending_split_check(connection, instrument=instrument, currency=currency)


@pytest.mark.anyio
async def test_an_instrument_waits_for_the_check_until_the_check_reaches_its_check_end(
    database_url: str, tmp_path: Path, gateway: FakeGatewayConnection
) -> None:
    import_bars(database_url, tmp_path, split_bars())
    serve_split_closes(gateway)

    waiting_before = [
        await read_pending(database_url, SPLT, "USD"),
        await read_pending(database_url, STAY, "USD"),
        await read_pending(database_url, None, "USD"),
        await read_pending(database_url, None, "HKD"),
    ]
    await run_check(database_url, gateway, WaitRecorder())

    assert waiting_before == [True, False, True, False]
    assert await read_pending(database_url, SPLT, "USD") is False
    assert await read_pending(database_url, None, "USD") is False
