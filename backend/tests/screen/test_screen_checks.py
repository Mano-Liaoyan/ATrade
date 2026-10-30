"""The checks of a screen (docs/architecture/screen.md section 24.6) through `POST /api/screens`.

Each problem gives the location of the condition in the request body and the reason.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx
import pytest

from tests.screen.test_screen_routes import momentum_definition

type Body = dict[str, Any]
CONDITIONS = ("definition", "indicator_conditions")


@dataclass(frozen=True)
class CheckCase:
    test_id: str
    change: Callable[[Body], None]
    problems: list[dict[str, Any]]


def set_value(*path: str | int, value: object) -> Callable[[Body], None]:
    def change(body: Body) -> None:
        target: Any = body
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value

    return change


def delete_key(*path: str | int) -> Callable[[Body], None]:
    def change(body: Body) -> None:
        target: Any = body
        for key in path[:-1]:
            target = target[key]
        del target[path[-1]]

    return change


def problem(location: list[str | int], message: str) -> dict[str, Any]:
    return {"location": location, "message": message}


CASES = [
    CheckCase(
        "start instruments of another market",
        set_value("definition", "start", value="hk_instrument_list"),
        [
            problem(
                ["definition", "start"],
                "The start instruments 'hk_instrument_list' do not belong to the market US. "
                "Known start instruments: quarter_universe, all_with_daily_bars, watchlist.",
            )
        ],
    ),
    CheckCase(
        "unknown market",
        set_value("market", value="JP"),
        [problem(["market"], "Unknown market 'JP'. Known markets: US, HK.")],
    ),
    CheckCase(
        "indicator not in the catalog",
        set_value(*CONDITIONS, 0, "indicator", "indicator", value="vwap"),
        [
            problem(
                [*CONDITIONS, 0, "indicator", "indicator"],
                "Unknown indicator 'vwap'. Known indicators: sma, ema, momentum_12_1, distance_to_52_week_high, "
                "realized_volatility, atr, average_trading_value, rsi, macd, bollinger_bands, donchian_channel.",
            )
        ],
    ),
    CheckCase(
        "output that does not belong to the indicator",
        set_value(*CONDITIONS, 0, "indicator", "output", value="signal"),
        [problem([*CONDITIONS, 0, "indicator", "output"], "Unknown output 'signal' of RSI. Known outputs: value.")],
    ),
    CheckCase(
        "parameter out of its range",
        set_value("definition", "order", "indicator", "parameters", "look_back", value=2000),
        [
            problem(
                ["definition", "order", "indicator", "parameters", "look_back"],
                "The look_back must be from 1 to 1000, not 2000.",
            )
        ],
    ),
    CheckCase(
        "rank percent above 100",
        set_value(*CONDITIONS, 2, "percent", value=101),
        [problem([*CONDITIONS, 2, "percent"], "The percent must be an integer from 1 to 100, not 101.")],
    ),
    CheckCase(
        "rank percent that is not an integer",
        set_value(*CONDITIONS, 2, "percent", value=20.5),
        [problem([*CONDITIONS, 2, "percent"], "The percent must be an integer from 1 to 100, not 20.5.")],
    ),
    CheckCase(
        "unknown operator",
        set_value("definition", "filters", 1, "operator", value="!="),
        [problem(["definition", "filters", 1, "operator"], "Unknown operator '!='. Known: <, <=, >, >=.")],
    ),
    CheckCase(
        "unknown filter field",
        set_value("definition", "filters", 0, "field", value="market_cap"),
        [
            problem(
                ["definition", "filters", 0, "field"],
                "Unknown field 'market_cap'. Known: still_trading, last_price, average_trading_value_20, exchange.",
            )
        ],
    ),
    CheckCase(
        "unknown condition kind",
        set_value(*CONDITIONS, 1, "kind", value="cross"),
        [problem([*CONDITIONS, 1, "kind"], "Unknown kind 'cross'. Known: compare, close_versus_line, rank.")],
    ),
    CheckCase(
        "unknown key",
        set_value("definition", "order", "limit", value=5),
        [problem(["definition", "order", "limit"], "Unknown key 'limit'. Known: indicator, direction, keep_first.")],
    ),
    CheckCase(
        "missing key",
        delete_key("definition", "order", "direction"),
        [problem(["definition", "order", "direction"], "The key 'direction' is missing.")],
    ),
    CheckCase(
        "unknown side",
        set_value(*CONDITIONS, 1, "side", value="through"),
        [problem([*CONDITIONS, 1, "side"], "Unknown side 'through'. Known: above, below.")],
    ),
    CheckCase(
        "line that is not SMA, EMA, or the Donchian upper line",
        set_value(*CONDITIONS, 1, "indicator", value={"indicator": "rsi", "parameters": {}, "output": "value"}),
        [
            problem(
                [*CONDITIONS, 1, "indicator"],
                "The line must be one of: sma value, ema value, donchian_channel upper. Not 'rsi' 'value'.",
            )
        ],
    ),
    CheckCase(
        "number that is not a decimal string",
        set_value(*CONDITIONS, 0, "value", value=30),
        [problem([*CONDITIONS, 0, "value"], 'The value must be a decimal string, for example "30", not 30.')],
    ),
    CheckCase(
        "keep_first above 500",
        set_value("definition", "order", "keep_first", value=501),
        [problem(["definition", "order", "keep_first"], "The keep_first must be an integer from 1 to 500, not 501.")],
    ),
    CheckCase(
        "exchange filter without exchanges",
        set_value("definition", "filters", 3, "values", value=[]),
        [problem(["definition", "filters", 3, "values"], "The values must be a list of 1 or more exchanges.")],
    ),
    CheckCase(
        "name longer than 100 characters",
        set_value("name", value="x" * 101),
        [problem(["name"], "The name must have 1 to 100 characters, not 101.")],
    ),
]


@pytest.mark.anyio
@pytest.mark.parametrize("case", CASES, ids=[case.test_id for case in CASES])
async def test_a_screen_that_is_not_correct_gives_the_location_and_the_reason(
    web_client: httpx.AsyncClient, case: CheckCase
) -> None:
    body: Body = {"name": "Momentum leaders", "market": "US", "definition": momentum_definition()}
    case.change(body)

    response = await web_client.post("/api/screens", json=body)

    assert response.status_code == httpx.codes.UNPROCESSABLE_ENTITY
    assert response.json() == {"problems": case.problems}


@pytest.mark.anyio
async def test_a_screen_with_the_largest_values_and_keep_first_is_correct(web_client: httpx.AsyncClient) -> None:
    definition = momentum_definition()
    definition["indicator_conditions"][2]["percent"] = 100
    definition["indicator_conditions"][1]["indicator"] = {
        "indicator": "donchian_channel",
        "parameters": {"period": 1000},
        "output": "upper",
    }
    definition["order"]["keep_first"] = 500

    response = await web_client.post("/api/screens", json={"name": "x" * 100, "market": "US", "definition": definition})

    assert response.status_code == httpx.codes.CREATED
