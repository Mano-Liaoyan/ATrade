"""The daily bar update of the `web` process: IBKR fake, fixed clock, and real PostgreSQL
(docs/architecture/market_data.md section 8.11)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import psycopg
import pytest

from atrade.foundation.bar import Bar, BarPeriod, TimeRange
from atrade.foundation.instrument import Instrument
from atrade.market_data import (
    BarRequest,
    BarSource,
    DailyBarUpdate,
    read_daily_bar_summaries,
    read_saved_bars,
    read_stock_split_candidates,
    save_received_bars,
)
from tests.fakes.clock import FixedClock
from tests.fakes.ibkr import FakeGatewayConnection, HistoricalBarRequest

APPLE = Instrument(symbol="AAPL", exchange="NASDAQ", currency="USD")
TENCENT = Instrument(symbol="700", exchange="SEHK", currency="HKD")
TESLA = Instrument(symbol="TSLA", exchange="NASDAQ", currency="USD")
# Wednesday 3 December 2025, 18:30 ET: after the US close and after the Hong Kong close.
AFTER_CLOSE_UTC = datetime(2025, 12, 3, 23, 30, tzinfo=UTC)
DECEMBER_3_UTC = datetime(2025, 12, 3, tzinfo=UTC)
DECEMBER_2_UTC = datetime(2025, 12, 2, tzinfo=UTC)
# The first trading day of the fourth quarter of 2025.
QUARTER_START_UTC = datetime(2025, 10, 1, tzinfo=UTC)


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

    first_read_start_utc = DECEMBER_3_UTC - timedelta(days=366)
    assert gateway_connection.historical_bar_requests == [
        HistoricalBarRequest(APPLE, BarPeriod.ONE_DAY, TimeRange(DECEMBER_2_UTC, DECEMBER_3_UTC)),
        HistoricalBarRequest(TENCENT, BarPeriod.ONE_DAY, TimeRange(first_read_start_utc, DECEMBER_3_UTC)),
        HistoricalBarRequest(TESLA, BarPeriod.ONE_DAY, TimeRange(first_read_start_utc, DECEMBER_3_UTC)),
    ]
    saved_bars = await read_saved_bars(
        database_url=database_url,
        bar_request=BarRequest(TENCENT, BarPeriod.ONE_DAY, TimeRange(first_read_start_utc, DECEMBER_3_UTC)),
        source_order=[BarSource.IBKR, BarSource.DATABENTO],
    )
    assert saved_bars.bar_counts[BarSource.IBKR] == 366
    summaries = await read_daily_bar_summaries(database_url=database_url, instruments=[APPLE, TENCENT, TESLA])
    # The fake bar of 2025-12-02 is day 20424 from the epoch: close 100 + 20424 % 50 + 0.5 = 124.5.
    assert [(summary.instrument, summary.last_day_start_utc, summary.last_close) for summary in summaries] == [
        (APPLE, DECEMBER_2_UTC, Decimal("124.5")),
        (TENCENT, DECEMBER_2_UTC, Decimal("124.5")),
        (TESLA, DECEMBER_2_UTC, Decimal("124.5")),
    ]


@pytest.mark.anyio
async def test_runs_1_time_on_each_trading_day_and_not_before_18_00_et(
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
    update = create_update(database_url, gateway_connection, AFTER_CLOSE_UTC)

    assert await update.update_if_due() is True

    candidates = await read_stock_split_candidates(database_url=database_url)
    assert [(item.instrument, item.ex_date_utc, item.split_ratio) for item in candidates] == [
        (APPLE, DECEMBER_3_UTC, Decimal(2))
    ]
    summaries = await read_daily_bar_summaries(database_url=database_url, instruments=[APPLE])
    assert [summary.last_close for summary in summaries] == [stored_close]
