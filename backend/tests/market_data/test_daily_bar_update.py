"""The daily bar update of the `web` process: IBKR fake, fixed clock, and real PostgreSQL
(docs/architecture/market_data.md section 8.11)."""

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import psycopg
import pytest

from atrade.foundation.bar import Bar, BarPeriod, TimeRange
from atrade.foundation.instrument import Instrument
from atrade.ibkr import GatewayRequestError
from atrade.market_data import (
    BarRequest,
    BarSource,
    DailyBarUpdate,
    daily_bar_update,
    read_daily_bar_summaries,
    read_saved_bars,
    read_stock_split_candidates,
    save_received_bars,
)
from atrade.market_data.daily_bar_update import UPDATE_TIME_ET
from tests.fakes.clock import FixedClock
from tests.fakes.ibkr import FakeGatewayConnection, HistoricalBarRequest

APPLE = Instrument(symbol="AAPL", exchange="NASDAQ", currency="USD")
TENCENT = Instrument(symbol="700", exchange="SEHK", currency="HKD")
TESLA = Instrument(symbol="TSLA", exchange="NASDAQ", currency="USD")
NEW_YORK = ZoneInfo("America/New_York")
# Wednesday 3 December 2025, 21:30 ET: after the US close and after the Hong Kong close.
AFTER_CLOSE_UTC = datetime(2025, 12, 4, 2, 30, tzinfo=UTC)
DECEMBER_4_UTC = datetime(2025, 12, 4, tzinfo=UTC)
DECEMBER_3_UTC = datetime(2025, 12, 3, tzinfo=UTC)
DECEMBER_2_UTC = datetime(2025, 12, 2, tzinfo=UTC)
# The first trading day of the fourth quarter of 2025.
QUARTER_START_UTC = datetime(2025, 10, 1, tzinfo=UTC)


class LinkLossGateway(FakeGatewayConnection):
    """The first read times out and loses the IBKR link. Like the real connection, each read then fails at once."""

    def __init__(self, *, link_returns_in_the_wait: bool) -> None:
        super().__init__(managed_accounts=["DU1234567"])
        self.connected = True
        self.link_returns_in_the_wait = link_returns_in_the_wait
        self.timeout_count = 0

    def is_connected(self) -> bool:
        connected = super().is_connected()
        if not connected and self.link_returns_in_the_wait:
            self.has_ibkr_connection = True
        return connected

    async def read_historical_bars(
        self, instrument: Instrument, bar_period: BarPeriod, time_range: TimeRange
    ) -> list[Bar]:
        if self.timeout_count == 0:
            self.timeout_count = 1
            self.has_ibkr_connection = False
            message = "IB Gateway did not answer the historical data request in time."
            raise GatewayRequestError(message)
        if not self.has_ibkr_connection:
            message = "IB Gateway has no connection to IBKR."
            raise GatewayRequestError(message)
        return await super().read_historical_bars(instrument, bar_period, time_range)


def save_update_instruments(database_url: str) -> None:
    """APPLE is a member of the current US universe, TENCENT is in the HK instrument list."""
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            """
            INSERT INTO us_universe_member (
                quarter_start_utc, rank, symbol, exchange, currency, average_trading_value, last_ranking_day_utc
            )
            VALUES (%(quarter_start_utc)s, 1, 'AAPL', 'NASDAQ', 'USD', 1000000, %(last_ranking_day_utc)s)
            """,
            {"quarter_start_utc": QUARTER_START_UTC, "last_ranking_day_utc": datetime(2025, 9, 30, tzinfo=UTC)},
        )
        connection.execute(
            """
            INSERT INTO hk_instrument_list_member (symbol, exchange, currency, added_at_utc)
            VALUES ('700', 'SEHK', 'HKD', now())
            """
        )


async def read_watchlist() -> list[Instrument]:
    return [TESLA, APPLE]


async def read_empty_watchlist() -> list[Instrument]:
    return []


def create_update(database_url: str, gateway_connection: FakeGatewayConnection, now_utc: datetime) -> DailyBarUpdate:
    return DailyBarUpdate(
        database_url=database_url,
        clock=FixedClock(now_utc),
        gateway_connection=gateway_connection,
        read_watchlist_instruments=read_watchlist,
    )


@pytest.fixture
def gateway_connection() -> FakeGatewayConnection:
    connection = FakeGatewayConnection(managed_accounts=["DU1234567"])
    connection.connected = True
    return connection


@pytest.mark.anyio
async def test_reads_the_daily_bars_of_the_universe_the_hk_list_and_the_watchlist_after_the_close(
    database_url: str, gateway_connection: FakeGatewayConnection
) -> None:
    save_update_instruments(database_url)
    # APPLE has IBKR daily bars to 2 December: the update reads 2 December again (stock split evidence).
    await save_received_bars(
        database_url=database_url,
        bar_request=BarRequest(APPLE, BarPeriod.ONE_DAY, TimeRange(DECEMBER_2_UTC, DECEMBER_3_UTC)),
        bars=[Bar(DECEMBER_2_UTC, Decimal(1), Decimal(125), Decimal(1), Decimal("124.5"), Decimal(1))],
    )
    update = create_update(database_url, gateway_connection, AFTER_CLOSE_UTC)

    assert await update.update_if_due() is True

    first_read_start_utc = DECEMBER_4_UTC - timedelta(days=366)
    assert gateway_connection.historical_bar_requests == [
        HistoricalBarRequest(APPLE, BarPeriod.ONE_DAY, TimeRange(DECEMBER_2_UTC, DECEMBER_4_UTC)),
        HistoricalBarRequest(TENCENT, BarPeriod.ONE_DAY, TimeRange(first_read_start_utc, DECEMBER_4_UTC)),
        HistoricalBarRequest(TESLA, BarPeriod.ONE_DAY, TimeRange(first_read_start_utc, DECEMBER_4_UTC)),
    ]
    saved_bars = await read_saved_bars(
        database_url=database_url,
        bar_request=BarRequest(TENCENT, BarPeriod.ONE_DAY, TimeRange(first_read_start_utc, DECEMBER_4_UTC)),
        source_order=[BarSource.IBKR, BarSource.DATABENTO],
    )
    assert saved_bars.bar_counts[BarSource.IBKR] == 366
    summaries = await read_daily_bar_summaries(database_url=database_url, instruments=[APPLE, TENCENT, TESLA])
    # The fake bar of 2025-12-03 is day 20425 from the epoch: close 100 + 20425 % 50 + 0.5 = 125.5.
    assert [(summary.instrument, summary.last_day_start_utc, summary.last_close) for summary in summaries] == [
        (APPLE, DECEMBER_3_UTC, Decimal("125.5")),
        (TENCENT, DECEMBER_3_UTC, Decimal("125.5")),
        (TESLA, DECEMBER_3_UTC, Decimal("125.5")),
    ]


@pytest.mark.anyio
@pytest.mark.parametrize("day", [date(2025, 7, 9), date(2025, 12, 3)], ids=["daylight_saving_time", "standard_time"])
async def test_the_first_minute_of_the_update_reads_the_daily_bar_of_that_day(
    database_url: str, gateway_connection: FakeGatewayConnection, day: date
) -> None:
    run_at_utc = datetime.combine(day, UPDATE_TIME_ET, NEW_YORK).astimezone(UTC)
    update = create_update(database_url, gateway_connection, run_at_utc)

    assert await update.update_if_due() is True

    end_utc = datetime.combine(day + timedelta(days=1), time(), UTC)
    assert {request.time_range.end_utc for request in gateway_connection.historical_bar_requests} == {end_utc}


@pytest.mark.anyio
async def test_a_quarter_without_saved_members_keeps_the_members_of_the_last_saved_quarter(
    database_url: str, gateway_connection: FakeGatewayConnection
) -> None:
    save_update_instruments(database_url)
    # Monday 5 January 2026, 21:30 ET: the first trading day of the quarter was 2 January.
    update = create_update(database_url, gateway_connection, datetime(2026, 1, 6, 2, 30, tzinfo=UTC))
    update.read_watchlist_instruments = read_empty_watchlist

    assert await update.update_if_due() is True

    assert [request.instrument for request in gateway_connection.historical_bar_requests] == [APPLE, TENCENT]


@pytest.mark.anyio
async def test_runs_1_time_on_each_trading_day_and_not_before_21_00_et(
    database_url: str, gateway_connection: FakeGatewayConnection
) -> None:
    before_time_update = create_update(database_url, gateway_connection, AFTER_CLOSE_UTC - timedelta(hours=1))
    saturday_update = create_update(database_url, gateway_connection, AFTER_CLOSE_UTC + timedelta(days=3))
    update = create_update(database_url, gateway_connection, AFTER_CLOSE_UTC)

    assert await before_time_update.update_if_due() is False
    assert await saturday_update.update_if_due() is False
    assert await update.update_if_due() is True
    assert await update.update_if_due() is False


@pytest.mark.anyio
async def test_does_not_run_that_day_when_ib_gateway_is_not_reachable(
    database_url: str, gateway_connection: FakeGatewayConnection
) -> None:
    save_update_instruments(database_url)
    await save_received_bars(
        database_url=database_url,
        bar_request=BarRequest(APPLE, BarPeriod.ONE_DAY, TimeRange(DECEMBER_2_UTC - timedelta(days=1), DECEMBER_2_UTC)),
        bars=[Bar(DECEMBER_2_UTC - timedelta(days=1), Decimal(1), Decimal(1), Decimal(1), Decimal(1), Decimal(1))],
    )
    gateway_connection.connected = False
    update = create_update(database_url, gateway_connection, AFTER_CLOSE_UTC)

    assert await update.update_if_due() is False

    gateway_connection.connected = True
    assert await update.update_if_due() is False
    assert gateway_connection.historical_bar_requests == []
    summaries = await read_daily_bar_summaries(database_url=database_url, instruments=[APPLE])
    assert [summary.last_day_start_utc for summary in summaries] == [DECEMBER_2_UTC - timedelta(days=1)]


@pytest.mark.anyio
async def test_the_update_after_a_start_waits_for_the_first_connection_and_logs_the_wait_1_time(
    database_url: str, caplog: pytest.LogCaptureFixture
) -> None:
    gateway_connection = FakeGatewayConnection(managed_accounts=["DU1234567"])
    update = create_update(database_url, gateway_connection, AFTER_CLOSE_UTC)

    assert await update.update_if_due() is False
    assert await update.update_if_due() is False

    assert len([record for record in caplog.records if "waits" in record.message]) == 1
    gateway_connection.connected = True
    assert await update.update_if_due() is True
    assert await update.update_if_due() is False


@pytest.mark.anyio
async def test_a_failed_read_of_one_instrument_does_not_stop_the_update(
    database_url: str, gateway_connection: FakeGatewayConnection
) -> None:
    save_update_instruments(database_url)
    gateway_connection.historical_bars_error_message = "No market data permissions"
    update = create_update(database_url, gateway_connection, AFTER_CLOSE_UTC)

    assert await update.update_if_due() is True

    assert len(gateway_connection.historical_bar_requests) == 3
    assert await read_daily_bar_summaries(database_url=database_url, instruments=[APPLE, TENCENT, TESLA]) == []


@pytest.mark.anyio
async def test_a_lost_ibkr_link_stops_the_update_and_a_later_minute_runs_it_again(
    database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(daily_bar_update, "IBKR_LINK_WAIT_SECONDS", 0)
    save_update_instruments(database_url)
    gateway_connection = LinkLossGateway(link_returns_in_the_wait=False)
    update = create_update(database_url, gateway_connection, AFTER_CLOSE_UTC)

    assert await update.update_if_due() is True
    assert await update.update_if_due() is False

    gateway_connection.has_ibkr_connection = True
    assert await update.update_if_due() is True
    assert await update.update_if_due() is False
    summaries = await read_daily_bar_summaries(database_url=database_url, instruments=[APPLE, TENCENT, TESLA])
    assert len(summaries) == 3


@pytest.mark.anyio
async def test_the_update_continues_when_the_ibkr_link_returns_in_the_wait(
    database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(daily_bar_update, "IBKR_LINK_WAIT_SECONDS", 0)
    save_update_instruments(database_url)
    gateway_connection = LinkLossGateway(link_returns_in_the_wait=True)
    update = create_update(database_url, gateway_connection, AFTER_CLOSE_UTC)

    assert await update.update_if_due() is True

    assert await update.update_if_due() is False
    assert len(gateway_connection.historical_bar_requests) == 2


@pytest.mark.anyio
async def test_the_day_that_is_read_again_gives_evidence_a_and_keeps_its_stored_close(
    database_url: str, gateway_connection: FakeGatewayConnection
) -> None:
    # The stored close of 2 December is 249. The fake IBKR close is 124.5: a stock split of 2 on 3 December.
    stored_close = Decimal(249)
    await save_received_bars(
        database_url=database_url,
        bar_request=BarRequest(APPLE, BarPeriod.ONE_DAY, TimeRange(DECEMBER_2_UTC, DECEMBER_3_UTC)),
        bars=[Bar(DECEMBER_2_UTC, stored_close, stored_close, stored_close, stored_close, Decimal(1))],
    )
    # The run of 2 December reads only 2 December.
    update = create_update(database_url, gateway_connection, AFTER_CLOSE_UTC - timedelta(days=1))

    assert await update.update_if_due() is True

    candidates = await read_stock_split_candidates(database_url=database_url)
    assert [(item.instrument, item.ex_date_utc, item.split_ratio) for item in candidates] == [
        (APPLE, DECEMBER_3_UTC, Decimal(2))
    ]
    summaries = await read_daily_bar_summaries(database_url=database_url, instruments=[APPLE])
    assert [summary.last_close for summary in summaries] == [stored_close]
