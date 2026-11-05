"""GET /api/market-data/indicators and POST /api/market-data/indicator-series (indicator.md section 23.9.6).

Real PostgreSQL and the IBKR fake. The tests save the bars directly in the bar tables, as a bar source writer does.
"""

import asyncio
import math
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import psycopg
import pytest
from psycopg import sql

from atrade.app.web import create_web_app
from atrade.foundation.bar import Bar
from atrade.foundation.instrument import Instrument
from atrade.foundation.settings import Settings
from atrade.indicator import INDICATOR_CATALOG, create_indicator
from atrade.market_data import indicator_series
from tests.fakes.clock import FixedClock
from tests.fakes.ibkr import FakeGatewayConnection

INDICATORS_PATH = "/api/market-data/indicators"
SERIES_PATH = "/api/market-data/indicator-series"
BARS_PATH = "/api/market-data/bars"
APPLE = Instrument(symbol="AAPL", exchange="NASDAQ", currency="USD")
FIRST_DAY = datetime(2025, 1, 1, tzinfo=UTC)
SAVED_RANGE_END = datetime(2025, 12, 31, tzinfo=UTC)


def day(number: int) -> datetime:
    """Day `number` from 1 January 2025 (day 0)."""
    return FIRST_DAY + timedelta(days=number)


def unix_seconds(time_utc: datetime) -> int:
    return int(time_utc.timestamp())


def make_wave_bars(count: int) -> list[Bar]:
    """Daily bars with a wave and a slow trend, so that each indicator of the catalog changes from bar to bar."""
    bars: list[Bar] = []
    for number in range(count):
        close = Decimal(f"{100 + 10 * math.sin(number / 9) + number * 0.05:.2f}")
        bars.append(
            Bar(
                start_utc=day(number),
                open=close - Decimal("0.50"),
                high=close + Decimal(1 + number % 3),
                low=close - Decimal(1 + number % 2),
                close=close,
                volume=Decimal(1000 + number * 10),
            )
        )
    return bars


def make_line_bars(count: int) -> list[Bar]:
    """Daily bars with close 100 + day number."""
    return [
        Bar(
            day(number),
            Decimal(100 + number),
            Decimal(100 + number),
            Decimal(100 + number),
            Decimal(100 + number),
            Decimal(1000),
        )
        for number in range(count)
    ]


def save_bars(database_url: str, bar_source: str, bars: list[Bar], start_utc: datetime = FIRST_DAY) -> None:
    """Saves daily APPLE bars and the saved range from `start_utc` to the end of 2025 in one bar source."""
    key = {"symbol": APPLE.symbol, "exchange": APPLE.exchange, "currency": APPLE.currency, "bar_period": "1-DAY"}
    with psycopg.connect(database_url, autocommit=True) as connection, connection.cursor() as cursor:
        cursor.executemany(
            sql.SQL("""
                INSERT INTO {} (symbol, exchange, currency, bar_period, start_utc, open, high, low, close, volume)
                VALUES (%(symbol)s, %(exchange)s, %(currency)s, %(bar_period)s, %(start_utc)s, %(open)s, %(high)s,
                    %(low)s, %(close)s, %(volume)s)
            """).format(sql.Identifier(f"{bar_source}_bar")),
            [
                {
                    **key,
                    "start_utc": bar.start_utc,
                    "open": bar.open,
                    "high": bar.high,
                    "low": bar.low,
                    "close": bar.close,
                    "volume": bar.volume,
                }
                for bar in bars
            ],
        )
        cursor.execute(
            sql.SQL("""
                INSERT INTO {} (symbol, exchange, currency, bar_period, start_utc, end_utc)
                VALUES (%(symbol)s, %(exchange)s, %(currency)s, %(bar_period)s, %(start_utc)s, %(end_utc)s)
            """).format(sql.Identifier(f"{bar_source}_bar_saved_range")),
            {**key, "start_utc": start_utc, "end_utc": SAVED_RANGE_END},
        )


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


def series_body(start_utc: datetime, end_utc: datetime, indicators: list[Any], **fields: Any) -> dict[str, Any]:
    return {
        "symbol": APPLE.symbol,
        "exchange": APPLE.exchange,
        "currency": APPLE.currency,
        "bar_period": "1-DAY",
        "start_utc": start_utc.isoformat(),
        "end_utc": end_utc.isoformat(),
        "indicators": indicators,
        **fields,
    }


async def read_series(
    client: httpx.AsyncClient, start_utc: datetime, end_utc: datetime, indicators: list[Any], **fields: Any
) -> httpx.Response:
    return await client.post(SERIES_PATH, json=series_body(start_utc, end_utc, indicators, **fields))


def calculate_screen_values(key: str, bars: list[Bar], first_index: int) -> dict[str, list[float | None]]:
    """The screen path: `update(bar)` with the look-back bars of the screen before `first_index`, then the bars."""
    definition = INDICATOR_CATALOG[key]
    indicator = create_indicator({"indicator": key}, has_output=False)
    look_back = definition.screen_look_back_bars({})
    values: dict[str, list[float | None]] = {output: [] for output in definition.outputs}
    for index, bar in enumerate(bars[first_index - look_back :]):
        indicator.update(bar)
        if index >= look_back:
            for output, output_values in values.items():
                value = getattr(indicator, output)
                output_values.append(None if value is None else float(value))
    return values


@pytest.mark.anyio
async def test_the_catalog_route_gives_the_short_name_and_the_chart_placement(client: httpx.AsyncClient) -> None:
    response = await client.get(INDICATORS_PATH)

    assert response.status_code == httpx.codes.OK
    indicators = response.json()
    assert [(item["key"], item["short_name"], item["chart_placement"]) for item in indicators] == [
        ("sma", "SMA", "price"),
        ("ema", "EMA", "price"),
        ("momentum_12_1", "MOM 12-1", "own"),
        ("distance_to_52_week_high", "52W HIGH", "own"),
        ("realized_volatility", "RV", "own"),
        ("atr", "ATR", "own"),
        ("average_trading_value", "ATV", "own"),
        ("rsi", "RSI", "own"),
        ("macd", "MACD", "own"),
        ("bollinger_bands", "BB", "price"),
        ("donchian_channel", "DC", "price"),
        ("adr_percent", "ADR%", "own"),
    ]
    assert indicators[7] == {
        "key": "rsi",
        "name": "RSI",
        "short_name": "RSI",
        "chart_placement": "own",
        "parameters": [
            {"name": "period", "value_type": "int", "default": 14, "minimum": 1, "maximum": 1000, "is_in_name": True}
        ],
        "outputs": ["value"],
        "value_description": INDICATOR_CATALOG["rsi"].value_description,
    }


@pytest.mark.anyio
async def test_the_screen_indicator_route_gives_the_same_catalog(client: httpx.AsyncClient) -> None:
    chart_catalog = (await client.get(INDICATORS_PATH)).json()
    screen_catalog = (await client.get("/api/screen-indicators")).json()

    assert screen_catalog == chart_catalog


@pytest.mark.anyio
async def test_each_series_value_is_equal_to_the_screen_value(client: httpx.AsyncClient, database_url: str) -> None:
    bars = make_wave_bars(340)
    save_bars(database_url, "ibkr", bars)
    first_index = 300

    response = await read_series(client, day(first_index), day(340), [{"indicator": key} for key in INDICATOR_CATALOG])

    assert response.status_code == httpx.codes.OK
    answer = response.json()
    assert answer["times"] == [unix_seconds(day(number)) for number in range(first_index, 340)]
    for series in answer["series"]:
        expected = calculate_screen_values(series["indicator"], bars, first_index)
        assert series["outputs"] == expected, series["indicator"]
        assert all(value is not None for values in expected.values() for value in values), series["indicator"]


@pytest.mark.anyio
async def test_the_event_loop_keeps_running_while_the_route_calculates(
    client: httpx.AsyncClient, database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    save_bars(database_url, "ibkr", make_wave_bars(5))
    calculate = indicator_series.calculate_series

    def calculate_slowly(reference: Any, warm_up_bars: list[Bar], bars: list[Bar]) -> indicator_series.IndicatorSeries:
        time.sleep(0.1)
        return calculate(reference, warm_up_bars, bars)

    monkeypatch.setattr(indicator_series, "calculate_series", calculate_slowly)
    ticks = 0

    async def count_ticks() -> None:
        nonlocal ticks
        while True:
            await asyncio.sleep(0.001)
            ticks += 1

    counter = asyncio.create_task(count_ticks())
    response = await read_series(client, day(0), day(5), [{"indicator": "sma", "parameters": {"period": 2}}])
    counter.cancel()

    assert response.status_code == httpx.codes.OK
    assert ticks >= 10


@pytest.mark.anyio
async def test_the_answer_has_all_parameters_with_the_defaults(client: httpx.AsyncClient, database_url: str) -> None:
    save_bars(database_url, "ibkr", make_line_bars(30))

    response = await read_series(
        client, day(10), day(12), [{"indicator": "bollinger_bands", "parameters": {"period": 3}}]
    )

    assert response.json()["series"] == [
        {
            "indicator": "bollinger_bands",
            "parameters": {"period": 3, "k": 2.0},
            "outputs": {
                "upper": [pytest.approx(109 + 2 * math.sqrt(2 / 3)), pytest.approx(110 + 2 * math.sqrt(2 / 3))],
                "middle": [109.0, 110.0],
                "lower": [pytest.approx(109 - 2 * math.sqrt(2 / 3)), pytest.approx(110 - 2 * math.sqrt(2 / 3))],
            },
        }
    ]


@pytest.mark.anyio
async def test_warm_up_bars_give_a_value_at_the_first_bar_of_the_range(
    client: httpx.AsyncClient, database_url: str
) -> None:
    save_bars(database_url, "ibkr", make_line_bars(20))

    response = await read_series(client, day(5), day(9), [{"indicator": "sma", "parameters": {"period": 3}}])

    # SMA(3) at day 5 is the mean of the closes 103, 104, and 105.
    assert response.json()["series"][0]["outputs"] == {"value": [104.0, 105.0, 106.0, 107.0]}


@pytest.mark.anyio
async def test_without_warm_up_bars_the_first_values_are_null(client: httpx.AsyncClient, database_url: str) -> None:
    save_bars(database_url, "ibkr", make_line_bars(20))

    response = await read_series(client, day(0), day(5), [{"indicator": "sma", "parameters": {"period": 3}}])

    assert response.json()["series"][0]["outputs"] == {"value": [None, None, 101.0, 102.0, 103.0]}


@pytest.mark.anyio
async def test_the_series_route_does_not_call_ibkr(
    client: httpx.AsyncClient, database_url: str, gateway_connection: FakeGatewayConnection
) -> None:
    save_bars(database_url, "ibkr", make_line_bars(20), start_utc=day(10))

    # Days 0 to 9 are not saved. The bars route would read them from IBKR.
    response = await read_series(client, day(0), day(15), [{"indicator": "sma", "parameters": {"period": 3}}])

    assert response.status_code == httpx.codes.OK
    assert response.json()["times"] == [unix_seconds(day(number)) for number in range(10, 15)]
    assert gateway_connection.historical_bar_requests == []


@pytest.mark.anyio
async def test_the_series_and_the_bars_route_read_through_the_given_source_order(
    client: httpx.AsyncClient, database_url: str
) -> None:
    save_bars(database_url, "ibkr", make_line_bars(20))
    databento_bars = [
        Bar(bar.start_utc, bar.open * 2, bar.high * 2, bar.low * 2, bar.close * 2, bar.volume)
        for bar in make_line_bars(20)
    ]
    save_bars(database_url, "databento", databento_bars)
    sma = [{"indicator": "sma", "parameters": {"period": 1}}]

    global_order = await read_series(client, day(5), day(6), sma)
    databento_first = await read_series(client, day(5), day(6), sma, source_order=["databento", "ibkr"])
    bars = await client.get(
        BARS_PATH,
        params={
            "symbol": APPLE.symbol,
            "exchange": APPLE.exchange,
            "currency": APPLE.currency,
            "bar_period": "1-DAY",
            "start_utc": day(5).isoformat(),
            "end_utc": day(6).isoformat(),
            "source_order": ["databento", "ibkr"],
        },
    )

    assert global_order.json()["series"][0]["outputs"] == {"value": [105.0]}
    assert databento_first.json()["series"][0]["outputs"] == {"value": [210.0]}
    assert [bar["close"] for bar in bars.json()["bars"]] == [210.0]


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("start_utc", "end_utc", "fields", "detail"),
    [
        (day(5), day(5), {}, "start_utc must be before end_utc."),
        (day(0), day(30000), {}, "The range has more than 20000 bars of 1-DAY. Use a shorter range."),
        (day(0), day(5), {"source_order": ["ibkr", "ibkr"]}, "The source order has a bar source 2 times."),
    ],
)
async def test_refuses_the_range_and_source_order_problems_of_the_bars_route(
    client: httpx.AsyncClient, start_utc: datetime, end_utc: datetime, fields: dict[str, Any], detail: str
) -> None:
    response = await read_series(client, start_utc, end_utc, [{"indicator": "sma"}], **fields)

    assert response.status_code == httpx.codes.UNPROCESSABLE_ENTITY
    assert response.json() == {"detail": detail}


@pytest.mark.anyio
async def test_refuses_a_bars_route_source_order_with_a_missing_bar_source(client: httpx.AsyncClient) -> None:
    response = await client.get(
        BARS_PATH,
        params={
            "symbol": APPLE.symbol,
            "exchange": APPLE.exchange,
            "currency": APPLE.currency,
            "bar_period": "1-DAY",
            "start_utc": day(5).isoformat(),
            "end_utc": day(6).isoformat(),
            "source_order": ["ibkr"],
        },
    )

    assert response.status_code == httpx.codes.UNPROCESSABLE_ENTITY
    assert response.json() == {"detail": "The source order must hold all bar sources. Missing: databento."}


@pytest.mark.anyio
async def test_refuses_an_unknown_bar_period(client: httpx.AsyncClient) -> None:
    response = await client.post(SERIES_PATH, json={**series_body(day(0), day(5), []), "bar_period": "2-DAY"})

    assert response.status_code == httpx.codes.UNPROCESSABLE_ENTITY


@pytest.mark.anyio
async def test_refuses_each_indicator_problem_with_its_location(client: httpx.AsyncClient) -> None:
    indicators = [
        {"indicator": "sma", "parameters": {"period": 0}},
        {"indicator": "vwap"},
        {"indicator": "bollinger_bands", "output": "upper"},
        {"indicator": "macd", "parameters": {"fast_period": 30}},
        "rsi",
    ]

    response = await read_series(client, day(0), day(5), indicators)

    assert response.status_code == httpx.codes.UNPROCESSABLE_ENTITY
    assert [problem["location"] for problem in response.json()["problems"]] == [
        ["indicators", 0, "parameters", "period"],
        ["indicators", 1, "indicator"],
        ["indicators", 2, "output"],
        ["indicators", 3, "parameters", "fast_period"],
        ["indicators", 4],
    ]
    assert response.json()["problems"][0]["message"] == "The period must be from 1 to 1000, not 0."
