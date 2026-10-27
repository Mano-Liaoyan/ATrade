"""GET /api/market-data/bars: reads bars from PostgreSQL and asks the IBKR fake only for the missing ranges."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from atrade.app import create_web_app
from atrade.foundation.bar import BarPeriod, TimeRange
from atrade.foundation.instrument import Instrument
from atrade.foundation.settings import Settings
from tests.fakes.clock import FixedClock
from tests.fakes.ibkr import FakeGatewayConnection, HistoricalBarRequest

BARS_PATH = "/api/market-data/bars"
TENCENT = Instrument(symbol="700", exchange="SEHK", currency="HKD")
APPLE = Instrument(symbol="AAPL", exchange="NASDAQ", currency="USD")


def utc(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 1, day, hour, minute, tzinfo=UTC)


def unix_seconds(time_utc: datetime) -> int:
    return int(time_utc.timestamp())


@pytest.fixture
def gateway_connection() -> FakeGatewayConnection:
    connection = FakeGatewayConnection(managed_accounts=["DU1234567"])
    connection.connected = True
    return connection


@pytest.fixture
async def client(
    database_url: str, clock: FixedClock, frontend_build_dir: Path, gateway_connection: FakeGatewayConnection
) -> AsyncIterator[httpx.AsyncClient]:
    settings = Settings(database_url=database_url, frontend_build_dir=frontend_build_dir)
    app = create_web_app(settings=settings, clock=clock, gateway_connection=gateway_connection)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http_client:
        yield http_client


async def read_bars(
    client: httpx.AsyncClient,
    instrument: Instrument,
    bar_period: str,
    start_utc: datetime | str,
    end_utc: datetime | str,
) -> httpx.Response:
    parameters = {
        "symbol": instrument.symbol,
        "exchange": instrument.exchange,
        "currency": instrument.currency,
        "bar_period": bar_period,
        "start_utc": start_utc if isinstance(start_utc, str) else start_utc.isoformat(),
        "end_utc": end_utc if isinstance(end_utc, str) else end_utc.isoformat(),
    }
    return await client.get(BARS_PATH, params=parameters)


def requested_ranges(gateway_connection: FakeGatewayConnection) -> list[TimeRange]:
    return [request.time_range for request in gateway_connection.historical_bar_requests]


@pytest.mark.anyio
async def test_returns_the_bars_of_the_range_with_unix_timestamps(
    client: httpx.AsyncClient, gateway_connection: FakeGatewayConnection
) -> None:
    response = await read_bars(client, TENCENT, "1-HOUR", utc(1, 0), utc(1, 2))

    assert response.status_code == 200
    # The fake bar of 2026-01-01 00:00 UTC is hour 490896 from the epoch: open 100 + 490896 % 50 = 146.
    assert response.json() == {
        "bars": [
            {"time": 1767225600, "open": 146.0, "high": 148.0, "low": 145.0, "close": 146.5, "volume": 1000.0},
            {"time": 1767229200, "open": 147.0, "high": 149.0, "low": 146.0, "close": 147.5, "volume": 1000.0},
        ]
    }
    assert gateway_connection.historical_bar_requests == [
        HistoricalBarRequest(TENCENT, BarPeriod.ONE_HOUR, TimeRange(utc(1, 0), utc(1, 2)))
    ]


@pytest.mark.anyio
async def test_does_not_call_ibkr_again_for_a_saved_range(
    client: httpx.AsyncClient, gateway_connection: FakeGatewayConnection
) -> None:
    first_response = await read_bars(client, TENCENT, "1-HOUR", utc(1, 0), utc(1, 6))
    gateway_connection.historical_bar_requests.clear()

    second_response = await read_bars(client, TENCENT, "1-HOUR", utc(1, 0), utc(1, 6))

    assert gateway_connection.historical_bar_requests == []
    assert second_response.json() == first_response.json()
    assert len(second_response.json()["bars"]) == 6


@pytest.mark.anyio
async def test_returns_saved_bars_while_the_gateway_is_not_reachable(
    client: httpx.AsyncClient, gateway_connection: FakeGatewayConnection
) -> None:
    await read_bars(client, TENCENT, "1-HOUR", utc(1, 0), utc(1, 6))
    gateway_connection.connected = False

    response = await read_bars(client, TENCENT, "1-HOUR", utc(1, 2), utc(1, 4))

    assert response.status_code == 200
    assert [bar["time"] for bar in response.json()["bars"]] == [unix_seconds(utc(1, 2)), unix_seconds(utc(1, 3))]


@pytest.mark.anyio
async def test_asks_ibkr_only_for_the_ranges_that_are_not_saved(
    client: httpx.AsyncClient, gateway_connection: FakeGatewayConnection
) -> None:
    await read_bars(client, TENCENT, "1-HOUR", utc(1, 4), utc(1, 6))
    await read_bars(client, TENCENT, "1-HOUR", utc(1, 10), utc(1, 12))
    gateway_connection.historical_bar_requests.clear()

    response = await read_bars(client, TENCENT, "1-HOUR", utc(1, 0), utc(1, 16))

    assert requested_ranges(gateway_connection) == [
        TimeRange(utc(1, 0), utc(1, 4)),
        TimeRange(utc(1, 6), utc(1, 10)),
        TimeRange(utc(1, 12), utc(1, 16)),
    ]
    assert [bar["time"] for bar in response.json()["bars"]] == [unix_seconds(utc(1, hour)) for hour in range(16)]


@pytest.mark.anyio
async def test_keeps_saved_ranges_apart_for_each_instrument_and_bar_period(
    client: httpx.AsyncClient, gateway_connection: FakeGatewayConnection
) -> None:
    await read_bars(client, TENCENT, "1-HOUR", utc(1, 0), utc(1, 2))
    gateway_connection.historical_bar_requests.clear()

    await read_bars(client, APPLE, "1-HOUR", utc(1, 0), utc(1, 2))
    await read_bars(client, TENCENT, "30-MINUTE", utc(1, 0), utc(1, 2))

    assert gateway_connection.historical_bar_requests == [
        HistoricalBarRequest(APPLE, BarPeriod.ONE_HOUR, TimeRange(utc(1, 0), utc(1, 2))),
        HistoricalBarRequest(TENCENT, BarPeriod.THIRTY_MINUTES, TimeRange(utc(1, 0), utc(1, 2))),
    ]


@pytest.mark.anyio
async def test_widens_the_range_to_whole_bar_periods(
    client: httpx.AsyncClient, gateway_connection: FakeGatewayConnection
) -> None:
    response = await read_bars(client, TENCENT, "1-HOUR", utc(1, 0, 30), utc(1, 1, 15))

    assert requested_ranges(gateway_connection) == [TimeRange(utc(1, 0), utc(1, 2))]
    assert [bar["time"] for bar in response.json()["bars"]] == [unix_seconds(utc(1, 0)), unix_seconds(utc(1, 1))]


@pytest.mark.anyio
async def test_does_not_save_the_current_bar_that_is_not_complete(
    client: httpx.AsyncClient, gateway_connection: FakeGatewayConnection
) -> None:
    # The fixed clock is 2026-01-02 03:04:05 UTC. The bar of 03:00 is not complete.
    response = await read_bars(client, TENCENT, "1-HOUR", utc(2, 1), utc(2, 6))

    assert requested_ranges(gateway_connection) == [TimeRange(utc(2, 1), utc(2, 3))]
    assert [bar["time"] for bar in response.json()["bars"]] == [unix_seconds(utc(2, 1)), unix_seconds(utc(2, 2))]


@pytest.mark.anyio
async def test_returns_no_bars_for_a_range_in_the_future(
    client: httpx.AsyncClient, gateway_connection: FakeGatewayConnection
) -> None:
    response = await read_bars(client, TENCENT, "1-HOUR", utc(5, 0), utc(5, 6))

    assert response.status_code == 200
    assert response.json() == {"bars": []}
    assert gateway_connection.historical_bar_requests == []


@pytest.mark.anyio
async def test_reports_unreachable_gateway_when_bars_are_missing(
    client: httpx.AsyncClient, gateway_connection: FakeGatewayConnection
) -> None:
    gateway_connection.connected = False

    response = await read_bars(client, TENCENT, "1-HOUR", utc(1, 0), utc(1, 2))

    assert response.status_code == 503
    assert response.json() == {
        "detail": "IB Gateway is not reachable at ib-gateway:4004. Bars that are not saved need IB Gateway."
    }


@pytest.mark.anyio
async def test_asks_ibkr_again_after_a_failed_request(
    client: httpx.AsyncClient, gateway_connection: FakeGatewayConnection
) -> None:
    gateway_connection.historical_bars_error_message = "Historical data request pacing violation"

    failed_response = await read_bars(client, TENCENT, "1-HOUR", utc(1, 0), utc(1, 2))
    gateway_connection.historical_bars_error_message = None
    gateway_connection.historical_bar_requests.clear()
    response = await read_bars(client, TENCENT, "1-HOUR", utc(1, 0), utc(1, 2))

    assert failed_response.status_code == 502
    assert failed_response.json() == {
        "detail": "Reading bars from IB Gateway failed: Historical data request pacing violation"
    }
    assert requested_ranges(gateway_connection) == [TimeRange(utc(1, 0), utc(1, 2))]
    assert len(response.json()["bars"]) == 2


@pytest.mark.anyio
async def test_reads_the_default_range_of_the_bar_period_up_to_now_without_times(
    client: httpx.AsyncClient, gateway_connection: FakeGatewayConnection
) -> None:
    parameters = {"symbol": "700", "exchange": "SEHK", "currency": "HKD", "bar_period": "1-HOUR"}

    response = await client.get(BARS_PATH, params=parameters)

    # The fixed clock is 2026-01-02 03:04:05 UTC. The default range of 1 hour bars is 90 days.
    assert requested_ranges(gateway_connection) == [
        TimeRange(datetime(2025, 10, 4, 3, tzinfo=UTC), datetime(2026, 1, 2, 3, tzinfo=UTC))
    ]
    assert len(response.json()["bars"]) == 90 * 24


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("bar_period", "start_utc", "end_utc"),
    [
        ("1-HOUR", "2026-01-01T02:00:00Z", "2026-01-01T02:00:00Z"),
        ("1-HOUR", "2026-01-01T02:00:00Z", "2026-01-01T01:00:00Z"),
        ("1-HOUR", "2026-01-01T00:00:00", "2026-01-01T02:00:00Z"),
        ("1-candle", "2026-01-01T00:00:00Z", "2026-01-01T02:00:00Z"),
        ("1-MINUTE", "2025-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
    ],
    ids=["empty range", "end before start", "no time zone", "unknown bar period", "too many bars"],
)
async def test_refuses_a_range_that_is_not_valid(
    client: httpx.AsyncClient,
    gateway_connection: FakeGatewayConnection,
    bar_period: str,
    start_utc: str,
    end_utc: str,
) -> None:
    response = await read_bars(client, TENCENT, bar_period, start_utc, end_utc)

    assert response.status_code == 422
    assert gateway_connection.historical_bar_requests == []
