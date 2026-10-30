"""The bar fetcher of the forward-test worker: it reads the daily bars of the members of multi-instrument forward tests
from IBKR and saves them in ibkr_bar (docs/architecture/forward_test.md section 12.20).

Real PostgreSQL, the IBKR fake, and a fixed clock. The member lists are fixed: the worker reads them from
forward_test_universe_member (test_universe_forward_test_child.py).
"""

from datetime import UTC, datetime, timedelta

import pytest

from atrade.forward_test import BarFetcher
from atrade.foundation.bar import BarPeriod, TimeRange
from atrade.foundation.instrument import Instrument
from atrade.market_data import BarRequest, BarSource, read_saved_bars, save_received_bars
from tests.fakes.clock import FixedClock
from tests.fakes.ibkr import FakeGatewayConnection, HistoricalBarRequest

APPLE = Instrument(symbol="AAPL", exchange="NASDAQ", currency="USD")
MICROSOFT = Instrument(symbol="MSFT", exchange="NASDAQ", currency="USD")
NVIDIA = Instrument(symbol="NVDA", exchange="NASDAQ", currency="USD")
DAILY = BarPeriod.ONE_DAY
# The fixed clock is 2026-01-02 03:04:05 UTC: after the daily close of 2026-01-01.
TODAY_UTC = datetime(2026, 1, 2, tzinfo=UTC)
ONE_YEAR_AGO_UTC = datetime(2025, 1, 2, tzinfo=UTC)
BAR_FETCHER_CLIENT_ID = 20


class SleepRecorder:
    """Records each wait of the bar fetcher and returns at once."""

    def __init__(self) -> None:
        self.seconds: list[float] = []

    async def sleep(self, seconds: float) -> None:
        self.seconds.append(seconds)


class MemberLists:
    """The members of each running multi-instrument forward test."""

    def __init__(self, member_lists: dict[int, list[Instrument]]) -> None:
        self.member_lists = member_lists

    async def read(self) -> dict[int, list[Instrument]]:
        return self.member_lists


def make_gateway() -> FakeGatewayConnection:
    return FakeGatewayConnection(managed_accounts=[], client_id=BAR_FETCHER_CLIENT_ID)


def make_bar_fetcher(
    database_url: str,
    clock: FixedClock,
    gateway: FakeGatewayConnection,
    member_lists: dict[int, list[Instrument]],
    sleep_recorder: SleepRecorder | None = None,
) -> BarFetcher:
    return BarFetcher(
        database_url=database_url,
        clock=clock,
        open_gateway_connection=lambda: gateway,
        read_member_lists=MemberLists(member_lists).read,
        sleep=(sleep_recorder or SleepRecorder()).sleep,
    )


async def read_ibkr_bar_count(database_url: str, instrument: Instrument) -> int:
    bar_request = BarRequest(instrument=instrument, bar_period=DAILY, time_range=TimeRange(ONE_YEAR_AGO_UTC, TODAY_UTC))
    saved_bars = await read_saved_bars(
        database_url=database_url, bar_request=bar_request, source_order=[BarSource.IBKR]
    )
    return saved_bars.bar_counts[BarSource.IBKR]


@pytest.mark.anyio
async def test_after_the_daily_close_it_saves_the_daily_bars_and_reads_a_shared_instrument_one_time(
    database_url: str, clock: FixedClock
) -> None:
    gateway = make_gateway()
    sleep_recorder = SleepRecorder()
    # 2 multi-instrument forward tests. Both have MSFT.
    bar_fetcher = make_bar_fetcher(
        database_url, clock, gateway, {1: [APPLE, MICROSOFT], 2: [MICROSOFT, NVIDIA]}, sleep_recorder
    )

    await bar_fetcher.fetch_when_due()

    one_year = TimeRange(ONE_YEAR_AGO_UTC, TODAY_UTC)
    assert gateway.historical_bar_requests == [
        HistoricalBarRequest(APPLE, DAILY, one_year),
        HistoricalBarRequest(MICROSOFT, DAILY, one_year),
        HistoricalBarRequest(NVIDIA, DAILY, one_year),
    ]
    # reqHistoricalData without keepUpToDate: no live bar subscription.
    assert gateway.live_bar_subscriptions == []
    assert sleep_recorder.seconds == [0.5, 0.5]
    # The fake market never closes: 1 bar for each day of the year.
    assert [await read_ibkr_bar_count(database_url, instrument) for instrument in (APPLE, MICROSOFT, NVIDIA)] == [
        365,
        365,
        365,
    ]
    assert not gateway.is_connected()


@pytest.mark.anyio
async def test_the_warm_up_fill_reads_only_the_ranges_that_no_bar_source_saved(
    database_url: str, clock: FixedClock
) -> None:
    gateway = make_gateway()
    saved_range = TimeRange(datetime(2025, 3, 1, tzinfo=UTC), datetime(2025, 9, 1, tzinfo=UTC))
    # Another writer (the bars route, a forward test warm-up) saved the middle of the year.
    await save_received_bars(
        database_url=database_url,
        bar_request=BarRequest(instrument=APPLE, bar_period=DAILY, time_range=saved_range),
        bars=[],
    )
    bar_fetcher = make_bar_fetcher(database_url, clock, gateway, {})

    await bar_fetcher.fill_warm_up([APPLE], datetime(2025, 12, 20, 14, 30, tzinfo=UTC))

    assert gateway.historical_bar_requests == [
        HistoricalBarRequest(APPLE, DAILY, TimeRange(datetime(2024, 12, 20, tzinfo=UTC), saved_range.start_utc)),
        HistoricalBarRequest(APPLE, DAILY, TimeRange(saved_range.end_utc, datetime(2025, 12, 20, tzinfo=UTC))),
    ]


@pytest.mark.anyio
async def test_a_second_save_of_the_same_bars_adds_no_row(database_url: str, clock: FixedClock) -> None:
    gateway = make_gateway()
    bar_fetcher = make_bar_fetcher(database_url, clock, gateway, {1: [APPLE]})
    await bar_fetcher.fetch_when_due()
    one_year = TimeRange(ONE_YEAR_AGO_UTC, TODAY_UTC)
    await gateway.connect()
    bars = await gateway.read_historical_bars(APPLE, DAILY, one_year)

    # The daily bar update of web can save the same instrument at the same time, with the same SQL.
    await save_received_bars(
        database_url=database_url,
        bar_request=BarRequest(instrument=APPLE, bar_period=DAILY, time_range=one_year),
        bars=bars,
    )

    assert await read_ibkr_bar_count(database_url, APPLE) == 365


@pytest.mark.anyio
async def test_when_ib_gateway_is_not_reachable_the_daily_read_runs_again_at_the_next_check(
    database_url: str, clock: FixedClock
) -> None:
    gateway = make_gateway()
    gateway.is_gateway_reachable = False
    bar_fetcher = make_bar_fetcher(database_url, clock, gateway, {1: [APPLE]})

    await bar_fetcher.fetch_when_due()

    assert await read_ibkr_bar_count(database_url, APPLE) == 0

    gateway.is_gateway_reachable = True
    await bar_fetcher.fetch_when_due()

    assert await read_ibkr_bar_count(database_url, APPLE) == 365


@pytest.mark.anyio
async def test_the_daily_read_runs_one_time_each_day_from_00_30_utc(database_url: str) -> None:
    gateway = make_gateway()
    clock = FixedClock(datetime(2026, 1, 2, 0, 15, tzinfo=UTC))
    bar_fetcher = make_bar_fetcher(database_url, clock, gateway, {1: [APPLE]})

    await bar_fetcher.fetch_when_due()
    assert gateway.historical_bar_requests == []

    clock.now_utc = datetime(2026, 1, 2, 0, 30, tzinfo=UTC)
    await bar_fetcher.fetch_when_due()
    await bar_fetcher.fetch_when_due()
    assert len(gateway.historical_bar_requests) == 1

    # The next day asks IBKR only for the new day.
    clock.now_utc += timedelta(days=1)
    await bar_fetcher.fetch_when_due()
    assert gateway.historical_bar_requests[1:] == [
        HistoricalBarRequest(APPLE, DAILY, TimeRange(TODAY_UTC, TODAY_UTC + timedelta(days=1)))
    ]


@pytest.mark.anyio
async def test_a_new_forward_test_gets_its_warm_up_before_the_daily_read_time(database_url: str) -> None:
    gateway = make_gateway()
    clock = FixedClock(datetime(2026, 1, 2, 0, 15, tzinfo=UTC))
    member_lists: dict[int, list[Instrument]] = {}
    bar_fetcher = make_bar_fetcher(database_url, clock, gateway, member_lists)

    member_lists[4] = [APPLE]
    assert not bar_fetcher.is_warm_up_filled(4)
    await bar_fetcher.fill_new_forward_tests()

    assert gateway.historical_bar_requests == [
        HistoricalBarRequest(APPLE, DAILY, TimeRange(ONE_YEAR_AGO_UTC, TODAY_UTC))
    ]
    assert bar_fetcher.is_warm_up_filled(4)
    # A filled forward test is not read again before the daily read.
    await bar_fetcher.fill_new_forward_tests()
    assert len(gateway.historical_bar_requests) == 1


@pytest.mark.anyio
async def test_without_ib_gateway_a_new_forward_test_stays_without_a_warm_up(
    database_url: str, clock: FixedClock
) -> None:
    gateway = make_gateway()
    gateway.is_gateway_reachable = False
    bar_fetcher = make_bar_fetcher(database_url, clock, gateway, {4: [APPLE]})

    await bar_fetcher.fill_new_forward_tests()

    assert not bar_fetcher.is_warm_up_filled(4)
