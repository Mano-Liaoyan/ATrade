"""The screen routes on the Web port (docs/architecture/screen.md section 24.7), with real PostgreSQL.

The clock is 2026-01-02 03:04:05 UTC.
"""

from typing import Any

import httpx
import psycopg
import pytest
from psycopg.types.json import Jsonb

NOW_TEXT = "2026-01-02T03:04:05Z"


def momentum_definition(start: str = "quarter_universe") -> dict[str, Any]:
    """The example of section 24.4.1, without `keep_first`."""
    return {
        "start": start,
        "filters": [
            {"field": "still_trading"},
            {"field": "last_price", "operator": ">", "value": "5"},
            {"field": "average_trading_value_20", "operator": ">", "value": "5000000"},
            {"field": "exchange", "values": ["NASDAQ", "NYSE"]},
        ],
        "indicator_conditions": [
            {
                "kind": "compare",
                "indicator": {"indicator": "rsi", "parameters": {"period": 14}, "output": "value"},
                "operator": "<",
                "value": "30",
            },
            {
                "kind": "close_versus_line",
                "indicator": {"indicator": "sma", "parameters": {"period": 200}, "output": "value"},
                "side": "above",
            },
            {
                "kind": "rank",
                "indicator": {"indicator": "momentum_12_1", "parameters": {}, "output": "value"},
                "end": "top",
                "percent": 20,
            },
        ],
        "order": {
            "indicator": {"indicator": "momentum_12_1", "parameters": {}, "output": "value"},
            "direction": "descending",
        },
    }


async def create_screen(client: httpx.AsyncClient, name: str = "Momentum leaders", market: str = "US") -> int:
    start = "quarter_universe" if market == "US" else "hk_instrument_list"
    response = await client.post(
        "/api/screens", json={"name": name, "market": market, "definition": momentum_definition(start)}
    )
    assert response.status_code == httpx.codes.CREATED, response.text
    return int(response.json()["id"])


@pytest.mark.anyio
async def test_a_new_screen_of_the_user_is_kept_and_has_no_conversation(web_client: httpx.AsyncClient) -> None:
    definition = momentum_definition()
    response = await web_client.post(
        "/api/screens", json={"name": "Momentum leaders", "market": "US", "definition": definition}
    )

    assert response.status_code == httpx.codes.CREATED
    body = response.json()
    assert body == {
        "id": body["id"],
        "name": "Momentum leaders",
        "market": "US",
        "definition": definition,
        "kept": True,
        "assistant_conversation_id": None,
        "created_at_utc": NOW_TEXT,
        "updated_at_utc": NOW_TEXT,
        "recent_screen_results": [],
    }


@pytest.mark.anyio
async def test_the_screen_list_has_the_name_market_kept_and_change_time(web_client: httpx.AsyncClient) -> None:
    first_id = await create_screen(web_client, "Momentum leaders", "US")
    second_id = await create_screen(web_client, "HK value", "HK")

    response = await web_client.get("/api/screens")

    assert response.status_code == httpx.codes.OK
    assert response.json() == [
        {"id": second_id, "name": "HK value", "market": "HK", "kept": True, "updated_at_utc": NOW_TEXT},
        {"id": first_id, "name": "Momentum leaders", "market": "US", "kept": True, "updated_at_utc": NOW_TEXT},
    ]


@pytest.mark.anyio
async def test_a_read_gives_the_screen_and_its_recent_screen_results(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    screen_id = await create_screen(web_client)
    with psycopg.connect(database_url, autocommit=True) as connection:
        for day, result_count in ((3, 12), (4, 7)):
            connection.execute(
                """
                INSERT INTO screen_result (
                    screen_id, run_at_utc, definition, market, daily_bars_date, run_seconds,
                    start_count, after_filters_count, after_indicator_conditions_count, result_count
                )
                VALUES (%(screen_id)s, %(run_at)s, %(definition)s, 'US', '2026-01-02', 0.3, 500, 200, 50, %(count)s)
                """,
                {
                    "screen_id": screen_id,
                    "run_at": f"2026-01-0{day}T10:00:00Z",
                    "definition": Jsonb(momentum_definition()),
                    "count": result_count,
                },
            )

    response = await web_client.get(f"/api/screens/{screen_id}")

    assert response.status_code == httpx.codes.OK
    body = response.json()
    assert body["name"] == "Momentum leaders"
    assert body["definition"] == momentum_definition()
    assert [(item["run_at_utc"], item["result_count"]) for item in body["recent_screen_results"]] == [
        ("2026-01-04T10:00:00Z", 7),
        ("2026-01-03T10:00:00Z", 12),
    ]


@pytest.mark.anyio
async def test_a_read_of_a_missing_screen_is_404(web_client: httpx.AsyncClient) -> None:
    response = await web_client.get("/api/screens/999")

    assert response.status_code == httpx.codes.NOT_FOUND
    assert response.json() == {"detail": "The screen 999 does not exist."}


@pytest.mark.anyio
async def test_a_change_overwrites_the_name_and_the_definition(web_client: httpx.AsyncClient) -> None:
    screen_id = await create_screen(web_client)
    definition = momentum_definition()
    definition["order"]["keep_first"] = 50

    response = await web_client.put(
        f"/api/screens/{screen_id}", json={"name": "Top 50 momentum", "definition": definition}
    )

    assert response.status_code == httpx.codes.OK
    body = response.json()
    assert (body["name"], body["market"], body["definition"]) == ("Top 50 momentum", "US", definition)
    read = await web_client.get(f"/api/screens/{screen_id}")
    assert read.json()["definition"]["order"]["keep_first"] == 50


@pytest.mark.anyio
async def test_a_change_of_a_missing_screen_is_404(web_client: httpx.AsyncClient) -> None:
    response = await web_client.put("/api/screens/999", json={"name": "X", "definition": momentum_definition()})

    assert response.status_code == httpx.codes.NOT_FOUND


@pytest.mark.anyio
async def test_a_delete_removes_the_screen(web_client: httpx.AsyncClient) -> None:
    screen_id = await create_screen(web_client)

    response = await web_client.delete(f"/api/screens/{screen_id}")

    assert response.status_code == httpx.codes.NO_CONTENT
    assert (await web_client.get(f"/api/screens/{screen_id}")).status_code == httpx.codes.NOT_FOUND
    assert (await web_client.get("/api/screens")).json() == []


@pytest.mark.anyio
async def test_a_delete_of_a_missing_screen_is_404(web_client: httpx.AsyncClient) -> None:
    response = await web_client.delete("/api/screens/999")

    assert response.status_code == httpx.codes.NOT_FOUND


@pytest.mark.anyio
async def test_a_second_screen_with_the_same_name_is_refused_with_a_problem(web_client: httpx.AsyncClient) -> None:
    await create_screen(web_client, "Momentum leaders")

    response = await web_client.post(
        "/api/screens",
        json={"name": "Momentum leaders", "market": "HK", "definition": momentum_definition("watchlist")},
    )

    assert response.status_code == httpx.codes.UNPROCESSABLE_ENTITY
    assert response.json() == {
        "problems": [{"location": ["name"], "message": "A screen with the name 'Momentum leaders' exists."}]
    }


@pytest.mark.anyio
async def test_a_change_to_the_name_of_another_screen_is_refused_with_a_problem(
    web_client: httpx.AsyncClient,
) -> None:
    await create_screen(web_client, "Momentum leaders")
    screen_id = await create_screen(web_client, "Value")

    response = await web_client.put(
        f"/api/screens/{screen_id}", json={"name": "Momentum leaders", "definition": momentum_definition()}
    )

    assert response.status_code == httpx.codes.UNPROCESSABLE_ENTITY
    assert response.json()["problems"][0]["location"] == ["name"]


@pytest.mark.anyio
async def test_a_screen_that_is_not_correct_is_refused_with_the_problem_list(web_client: httpx.AsyncClient) -> None:
    definition = momentum_definition()
    definition["start"] = "hk_instrument_list"
    definition["indicator_conditions"][0]["indicator"]["parameters"]["period"] = 0

    response = await web_client.post("/api/screens", json={"name": "", "market": "US", "definition": definition})

    assert response.status_code == httpx.codes.UNPROCESSABLE_ENTITY
    assert response.json() == {
        "problems": [
            {"location": ["name"], "message": "The name must have 1 to 100 characters, not 0."},
            {
                "location": ["definition", "start"],
                "message": "The start instruments 'hk_instrument_list' do not belong to the market US. "
                "Known start instruments: quarter_universe, all_with_daily_bars, watchlist.",
            },
            {
                "location": ["definition", "indicator_conditions", 0, "indicator", "parameters", "period"],
                "message": "The period must be from 1 to 1000, not 0.",
            },
        ]
    }
    assert (await web_client.get("/api/screens")).json() == []


@pytest.mark.anyio
async def test_a_change_that_is_not_correct_is_refused_and_keeps_the_screen(web_client: httpx.AsyncClient) -> None:
    screen_id = await create_screen(web_client)
    definition = momentum_definition()
    definition["indicator_conditions"][2]["percent"] = 0

    response = await web_client.put(f"/api/screens/{screen_id}", json={"name": "Changed", "definition": definition})

    assert response.status_code == httpx.codes.UNPROCESSABLE_ENTITY
    assert response.json()["problems"] == [
        {
            "location": ["definition", "indicator_conditions", 2, "percent"],
            "message": "The percent must be an integer from 1 to 100, not 0.",
        }
    ]
    assert (await web_client.get(f"/api/screens/{screen_id}")).json()["name"] == "Momentum leaders"


@pytest.mark.anyio
async def test_the_screen_indicator_list_gives_the_catalog_for_the_edit_popover(web_client: httpx.AsyncClient) -> None:
    response = await web_client.get("/api/screen-indicators")

    assert response.status_code == httpx.codes.OK
    indicators = {item["key"]: item for item in response.json()}
    assert list(indicators)[:3] == ["sma", "ema", "momentum_12_1"]
    assert indicators["rsi"] == {
        "key": "rsi",
        "name": "RSI",
        "parameters": [
            {"name": "period", "value_type": "int", "default": 14, "minimum": 1, "maximum": 1000, "is_in_name": True}
        ],
        "outputs": ["value"],
    }
    assert indicators["bollinger_bands"]["parameters"][1] == {
        "name": "k",
        "value_type": "float",
        "default": 2.0,
        "minimum": 0.1,
        "maximum": 10.0,
        "is_in_name": True,
    }
    assert indicators["macd"]["outputs"] == ["value", "signal", "histogram"]
    assert indicators["realized_volatility"]["parameters"][1]["is_in_name"] is False
