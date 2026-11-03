"""The chart indicator set routes (docs/architecture/indicator.md sections 23.9.6 and 23.9.7)."""

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import psycopg
import pytest
from alembic import command
from alembic.config import Config

from atrade.app.database_migrations import MIGRATIONS_DIR
from atrade.app.web import create_web_app
from atrade.foundation.settings import Settings
from tests.fakes.clock import FixedClock
from tests.fakes.ibkr import FakeGatewayConnection

CHART_INDICATORS_PATH = "/api/market-data/chart-indicators"
PREVIOUS_REVISION = "c4a81e6d2b07"


@pytest.fixture
async def client(database_url: str, clock: FixedClock, frontend_build_dir: Path) -> AsyncIterator[httpx.AsyncClient]:
    settings = Settings(database_url=database_url, frontend_build_dir=frontend_build_dir)
    app = create_web_app(settings=settings, clock=clock, gateway_connection=FakeGatewayConnection(managed_accounts=[]))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http_client:
        yield http_client


def line(output: str = "value", color: int = 1, style: str = "solid", width: int = 2) -> dict[str, Any]:
    return {"output": output, "color": color, "style": style, "width": width}


def sma(**line_fields: Any) -> dict[str, Any]:
    return {"indicator": "sma", "parameters": {"period": 50}, "hidden": False, "lines": [line(**line_fields)]}


def rsi() -> dict[str, Any]:
    return {"indicator": "rsi", "parameters": {"period": 14}, "hidden": True, "lines": [line(color=5)]}


def macd(parameters: dict[str, int]) -> dict[str, Any]:
    lines = [line("value"), line("signal"), line("histogram")]
    return {"indicator": "macd", "parameters": parameters, "hidden": False, "lines": lines}


def bollinger_bands(lines: list[dict[str, Any]]) -> dict[str, Any]:
    return {"indicator": "bollinger_bands", "parameters": {"period": 20, "k": 2}, "hidden": False, "lines": lines}


def chart_set(panes: list[list[dict[str, Any]]], favorites: list[str] | None = None) -> dict[str, Any]:
    return {"panes": [{"indicators": indicators} for indicators in panes], "favorites": favorites or []}


def test_the_migration_writes_the_price_pane_without_indicators_and_no_favorites(database_url: str) -> None:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    config.attributes["database_url"] = database_url
    command.downgrade(config, PREVIOUS_REVISION)
    command.upgrade(config, "head")

    with psycopg.connect(database_url, autocommit=True) as connection:
        rows = connection.execute("SELECT single_row, panes, favorites FROM chart_indicator_set").fetchall()
    assert rows == [(True, [{"indicators": []}], [])]


@pytest.mark.anyio
async def test_reads_the_set_of_the_migration(client: httpx.AsyncClient) -> None:
    response = await client.get(CHART_INDICATORS_PATH)

    assert response.status_code == 200
    assert response.json() == {"panes": [{"indicators": []}], "favorites": []}


@pytest.mark.anyio
async def test_reads_the_saved_set(client: httpx.AsyncClient) -> None:
    saved = chart_set(
        [
            [sma(color=3, style="dashed", width=4), bollinger_bands([line("upper"), line("middle"), line("lower")])],
            [rsi()],
        ],
        favorites=["rsi", "sma"],
    )

    put_response = await client.put(CHART_INDICATORS_PATH, json=saved)
    get_response = await client.get(CHART_INDICATORS_PATH)

    assert put_response.status_code == 200
    assert put_response.json() == saved
    assert get_response.json() == saved


@pytest.mark.anyio
async def test_the_last_save_wins(client: httpx.AsyncClient) -> None:
    await client.put(CHART_INDICATORS_PATH, json=chart_set([[sma()], [rsi()]], favorites=["sma"]))
    await client.put(CHART_INDICATORS_PATH, json=chart_set([[]], favorites=["rsi"]))

    response = await client.get(CHART_INDICATORS_PATH)

    assert response.json() == chart_set([[]], favorites=["rsi"])


THREE_BB_LINES = [line("upper"), line("middle"), line("lower")]


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("body", "location"),
    [
        pytest.param(chart_set([]), ["panes"], id="no pane"),
        pytest.param(chart_set([[], [rsi()], [rsi()], [rsi()], [rsi()]]), ["panes"], id="more than 4 panes"),
        pytest.param(chart_set([[sma()], []]), ["panes", 1, "indicators"], id="own pane without an indicator"),
        pytest.param(chart_set([[rsi()]]), ["panes", 0, "indicators", 0, "indicator"], id="own indicator in price"),
        pytest.param(chart_set([[], [rsi(), sma()]]), ["panes", 1, "indicators", 1, "indicator"], id="price in own"),
        pytest.param(
            chart_set([[{**sma(), "indicator": "unknown"}]]),
            ["panes", 0, "indicators", 0, "indicator"],
            id="unknown indicator",
        ),
        pytest.param(
            chart_set([[{**sma(), "parameters": {"period": 0}}]]),
            ["panes", 0, "indicators", 0, "parameters", "period"],
            id="parameter out of range",
        ),
        pytest.param(
            chart_set([[{**sma(), "parameters": {"length": 5}}]]),
            ["panes", 0, "indicators", 0, "parameters", "length"],
            id="unknown parameter",
        ),
        pytest.param(
            chart_set([[], [macd({"fast_period": 30, "slow_period": 26})]]),
            ["panes", 1, "indicators", 0, "parameters", "fast_period"],
            id="parameter order",
        ),
        pytest.param(
            chart_set([[bollinger_bands(THREE_BB_LINES[:2])]]),
            ["panes", 0, "indicators", 0, "lines"],
            id="missing output",
        ),
        pytest.param(
            chart_set([[bollinger_bands([*THREE_BB_LINES, line("upper")])]]),
            ["panes", 0, "indicators", 0, "lines", 3, "output"],
            id="output 2 times",
        ),
        pytest.param(
            chart_set([[bollinger_bands([*THREE_BB_LINES, line("average")])]]),
            ["panes", 0, "indicators", 0, "lines", 3, "output"],
            id="unknown output",
        ),
        pytest.param(chart_set([[sma(color=0)]]), ["panes", 0, "indicators", 0, "lines", 0, "color"], id="color 0"),
        pytest.param(chart_set([[sma(color=15)]]), ["panes", 0, "indicators", 0, "lines", 0, "color"], id="color 15"),
        pytest.param(
            chart_set([[sma(style="wavy")]]), ["panes", 0, "indicators", 0, "lines", 0, "style"], id="unknown style"
        ),
        pytest.param(chart_set([[sma(width=0)]]), ["panes", 0, "indicators", 0, "lines", 0, "width"], id="width 0"),
        pytest.param(chart_set([[sma(width=5)]]), ["panes", 0, "indicators", 0, "lines", 0, "width"], id="width 5"),
        pytest.param(chart_set([[]], favorites=["sma", "unknown"]), ["favorites", 1], id="unknown favorite"),
        pytest.param(chart_set([[]], favorites=["sma", "rsi", "sma"]), ["favorites", 2], id="favorite 2 times"),
    ],
)
async def test_refuses_a_set_with_a_problem_at_its_location(
    client: httpx.AsyncClient, body: dict[str, Any], location: list[str | int]
) -> None:
    response = await client.put(CHART_INDICATORS_PATH, json=body)

    assert response.status_code == 422
    problems = response.json()["problems"]
    assert [problem["location"] for problem in problems] == [location]
    assert all(problem["message"] for problem in problems)
    assert (await client.get(CHART_INDICATORS_PATH)).json() == chart_set([[]])
