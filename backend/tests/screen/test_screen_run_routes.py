"""The run route and the screen result route (docs/architecture/screen.md section 24.7), with real PostgreSQL and
saved daily bars (docs/architecture.md section 17.4).

The clock is 2026-01-02 03:04:05 UTC. The first trading day of that quarter is 2026-01-02.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx
import psycopg
import pytest
from psycopg.types.json import Jsonb

from atrade.foundation.bar import Bar, BarPeriod, TimeRange
from atrade.foundation.instrument import Instrument
from atrade.market_data import BarRequest, save_received_bars

LAST_DAY = datetime(2025, 12, 31, tzinfo=UTC)
NOW_UTC = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)


def stock(symbol: str, exchange: str = "NASDAQ", currency: str = "USD") -> Instrument:
    return Instrument(symbol=symbol, exchange=exchange, currency=currency)


async def save_daily_bars(database_url: str, instrument: Instrument, close: str, count: int = 5) -> None:
    """Saves `count` daily bars with the same close, the last one on 2025-12-31."""
    price = Decimal(close)
    first_day = LAST_DAY - timedelta(days=count - 1)
    bars = [
        Bar(
            start_utc=first_day + timedelta(days=index),
            open=price,
            high=price,
            low=price,
            close=price,
            volume=Decimal(1000),
        )
        for index in range(count)
    ]
    bar_request = BarRequest(instrument, BarPeriod.ONE_DAY, TimeRange(first_day, LAST_DAY + timedelta(days=1)))
    await save_received_bars(database_url=database_url, bar_request=bar_request, bars=bars)


def add_to_watchlist(database_url: str, *instruments: Instrument) -> None:
    with psycopg.connect(database_url, autocommit=True) as connection:
        for instrument in instruments:
            connection.execute(
                """
                INSERT INTO watchlist_instrument (symbol, exchange, currency, added_at_utc)
                VALUES (%s, %s, %s, %s)
                """,
                (instrument.symbol, instrument.exchange, instrument.currency, NOW_UTC),
            )


def sma(period: int) -> dict[str, Any]:
    return {"indicator": "sma", "parameters": {"period": period}, "output": "value"}


def make_definition(start: str = "watchlist", **parts: Any) -> dict[str, Any]:
    return {
        "start": start,
        "filters": [],
        "indicator_conditions": [],
        "order": {"indicator": sma(3), "direction": "descending"},
        **parts,
    }


async def create_screen(client: httpx.AsyncClient, definition: dict[str, Any], market: str = "US") -> int:
    name = f"{definition['start']} {market}"
    response = await client.post("/api/screens", json={"name": name, "market": market, "definition": definition})
    assert response.status_code == httpx.codes.CREATED, response.text
    return int(response.json()["id"])


async def run_screen(client: httpx.AsyncClient, definition: dict[str, Any], market: str = "US") -> dict[str, Any]:
    screen_id = await create_screen(client, definition, market)
    response = await client.post(f"/api/screens/{screen_id}/runs")
    assert response.status_code == httpx.codes.CREATED, response.text
    return response.json()


def symbols(body: dict[str, Any]) -> list[str]:
    return [row["symbol"] for row in body["rows"]]


@pytest.mark.anyio
async def test_a_run_saves_a_screen_result_that_the_read_route_gives_back(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    apple, microsoft, tesla, tencent = stock("AAPL"), stock("MSFT"), stock("TSLA"), stock("700", "SEHK", "HKD")
    await save_daily_bars(database_url, apple, "30")
    await save_daily_bars(database_url, microsoft, "20")
    await save_daily_bars(database_url, tesla, "10")
    await save_daily_bars(database_url, tencent, "40")
    add_to_watchlist(database_url, apple, microsoft, tesla, stock("NEW"), tencent)
    definition = make_definition(
        filters=[{"field": "last_price", "operator": ">", "value": "15"}],
        indicator_conditions=[{"kind": "rank", "indicator": sma(2), "end": "top", "percent": 100}],
    )

    created = await run_screen(web_client, definition)
    read = await web_client.get(f"/api/screen-results/{created['id']}")

    assert read.status_code == httpx.codes.OK
    assert read.json() == created
    run_seconds = created["summary"]["run_seconds"]
    assert run_seconds >= 0
    assert created == {
        "id": created["id"],
        "screen_id": created["screen_id"],
        "market": "US",
        "assistant_conversation_id": None,
        "definition": definition,
        # The UI names of the indicators of the definition: one for each indicator condition, and the order.
        "indicator_names": {"indicator_conditions": ["SMA(2)"], "order": "SMA(3)"},
        "summary": {
            "row_count": 2,
            "start_count": 4,
            "after_filters_count": 2,
            "after_indicator_conditions_count": 2,
            "result_count": 2,
            "exclusion_counts": [
                {"reason": "No daily bars", "count": 1},
                {"reason": "filters[0]: Close > 15", "count": 1},
            ],
            "daily_bars_date": "2025-12-31",
            "run_at_utc": "2026-01-02T03:04:05Z",
            "run_seconds": run_seconds,
        },
        "rows": [
            {
                "position": 1,
                "symbol": "AAPL",
                "exchange": "NASDAQ",
                "currency": "USD",
                "last_price": "30",
                "average_trading_value_20": None,
                "indicator_values": {"SMA(2)": 30.0, "SMA(3)": 30.0},
                "percentiles": {"SMA(2)": 100.0},
            },
            {
                "position": 2,
                "symbol": "MSFT",
                "exchange": "NASDAQ",
                "currency": "USD",
                "last_price": "20",
                "average_trading_value_20": None,
                "indicator_values": {"SMA(2)": 20.0, "SMA(3)": 20.0},
                "percentiles": {"SMA(2)": 50.0},
            },
        ],
        "exclusions": [
            {"symbol": "NEW", "exchange": "NASDAQ", "currency": "USD", "reason": "No daily bars"},
            {"symbol": "TSLA", "exchange": "NASDAQ", "currency": "USD", "reason": "filters[0]: Close > 15"},
        ],
    }


@pytest.mark.anyio
async def test_the_read_route_gives_one_page_of_rows(web_client: httpx.AsyncClient, database_url: str) -> None:
    instruments = [stock(f"S{number:02}") for number in range(1, 61)]
    for number, instrument in enumerate(instruments, start=1):
        await save_daily_bars(database_url, instrument, str(number), count=3)
    add_to_watchlist(database_url, *instruments)
    created = await run_screen(web_client, make_definition())

    second_page = await web_client.get(f"/api/screen-results/{created['id']}", params={"offset": 2, "limit": 3})

    assert len(created["rows"]) == 50
    assert created["summary"]["row_count"] == 60
    assert [(row["position"], row["symbol"]) for row in second_page.json()["rows"]] == [
        (3, "S58"),
        (4, "S57"),
        (5, "S56"),
    ]


@pytest.mark.anyio
async def test_the_start_instruments_of_each_kind(web_client: httpx.AsyncClient, database_url: str) -> None:
    member, other, tencent, alibaba = (
        stock("AAPL"),
        stock("MSFT"),
        stock("700", "SEHK", "HKD"),
        stock("9988", "SEHK", "HKD"),
    )
    for instrument in (member, other, tencent, alibaba):
        await save_daily_bars(database_url, instrument, "10")
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            """
            INSERT INTO us_universe_member (
                quarter_start_utc, rank, symbol, exchange, currency, average_trading_value, last_ranking_day_utc
            )
            VALUES ('2026-01-02', 1, 'AAPL', 'NASDAQ', 'USD', 1, '2025-12-31'),
                ('2025-10-01', 1, 'MSFT', 'NASDAQ', 'USD', 1, '2025-09-30')
            """
        )
        connection.execute(
            "INSERT INTO hk_instrument_list_member (symbol, exchange, currency, added_at_utc) VALUES (%s, %s, %s, %s)",
            ("700", "SEHK", "HKD", NOW_UTC),
        )

    starts = {
        "quarter_universe": await run_screen(web_client, make_definition("quarter_universe")),
        "all_with_daily_bars": await run_screen(web_client, make_definition("all_with_daily_bars")),
        "hk_instrument_list": await run_screen(web_client, make_definition("hk_instrument_list"), "HK"),
    }

    assert {start: sorted(symbols(body)) for start, body in starts.items()} == {
        "quarter_universe": ["AAPL"],
        "all_with_daily_bars": ["AAPL", "MSFT"],
        "hk_instrument_list": ["700"],
    }


@pytest.mark.anyio
async def test_the_run_of_a_screen_that_does_not_exist_gives_404(web_client: httpx.AsyncClient) -> None:
    run = await web_client.post("/api/screens/999/runs")
    read = await web_client.get("/api/screen-results/999")

    assert run.status_code == httpx.codes.NOT_FOUND
    assert read.status_code == httpx.codes.NOT_FOUND


@pytest.mark.anyio
async def test_the_run_of_a_saved_screen_that_fails_the_check_gives_the_problem_list(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    screen_id = await create_screen(web_client, make_definition())
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            "UPDATE screen SET definition = %s WHERE id = %s",
            (Jsonb(make_definition(order={"indicator": sma(0), "direction": "descending"})), screen_id),
        )

    response = await web_client.post(f"/api/screens/{screen_id}/runs")

    assert response.status_code == httpx.codes.UNPROCESSABLE_ENTITY
    problems = response.json()["problems"]
    assert [problem["location"] for problem in problems] == [
        ["definition", "order", "indicator", "parameters", "period"]
    ]


@pytest.mark.anyio
async def test_a_run_with_a_changed_definition_and_market_keeps_the_saved_screen(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    apple, microsoft, tencent = stock("AAPL"), stock("MSFT"), stock("700", "SEHK", "HKD")
    await save_daily_bars(database_url, apple, "30")
    await save_daily_bars(database_url, microsoft, "20")
    await save_daily_bars(database_url, tencent, "40")
    add_to_watchlist(database_url, apple, microsoft, tencent)
    saved = make_definition()
    screen_id = await create_screen(web_client, saved)
    changed = make_definition(filters=[{"field": "last_price", "operator": ">", "value": "25"}])

    us_run = await web_client.post(f"/api/screens/{screen_id}/runs", json={"market": "US", "definition": changed})
    hk_run = await web_client.post(f"/api/screens/{screen_id}/runs", json={"market": "HK", "definition": saved})
    screen = await web_client.get(f"/api/screens/{screen_id}")

    assert us_run.status_code == httpx.codes.CREATED, us_run.text
    assert symbols(us_run.json()) == ["AAPL"]
    assert us_run.json()["definition"] == changed
    assert hk_run.json()["market"] == "HK"
    assert symbols(hk_run.json()) == ["700"]
    assert screen.json()["definition"] == saved
    assert screen.json()["market"] == "US"


@pytest.mark.anyio
async def test_a_run_with_a_changed_definition_that_fails_the_check_gives_the_problem_list(
    web_client: httpx.AsyncClient,
) -> None:
    screen_id = await create_screen(web_client, make_definition())
    changed = make_definition(filters=[{"field": "last_price", "operator": "?", "value": "25"}])

    response = await web_client.post(f"/api/screens/{screen_id}/runs", json={"market": "US", "definition": changed})

    assert response.status_code == httpx.codes.UNPROCESSABLE_ENTITY
    locations = [problem["location"] for problem in response.json()["problems"]]
    assert ["definition", "filters", 0, "operator"] in locations
