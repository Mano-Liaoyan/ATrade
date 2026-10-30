"""A `list` universe from a screen result: `screen_result_id` and the optional `symbols` (docs/architecture/backtest.md
section 10.10.6, docs/architecture/screen.md section 24.9)."""

from datetime import UTC, datetime

import httpx
import psycopg
import pytest
from psycopg.types.json import Jsonb

from atrade.foundation.instrument import Instrument
from tests.backtest.test_backtest_routes import save_test_strategy_version
from tests.backtest.test_universe_backtest_routes import count_backtests, read_universe_members
from tests.backtest.universe_data import AAA, CCC, RANGE_START_UTC, make_universe_request, save_universe_test_data

NOW_UTC = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)


def save_screen_result(database_url: str, members: list[Instrument]) -> int:
    with psycopg.connect(database_url, autocommit=True) as connection:
        screen = connection.execute(
            """
            INSERT INTO screen (name, market, definition, kept, created_at_utc, updated_at_utc)
            VALUES ('Momentum', 'US', %(definition)s, true, %(now)s, %(now)s) RETURNING id
            """,
            {"definition": Jsonb({}), "now": NOW_UTC},
        ).fetchone()
        assert screen is not None
        result = connection.execute(
            """
            INSERT INTO screen_result (
                screen_id, run_at_utc, definition, market, daily_bars_date, run_seconds,
                start_count, after_filters_count, after_indicator_conditions_count, result_count
            )
            VALUES (%(screen_id)s, %(now)s, %(definition)s, 'US', '2026-01-01', 0.5, 10, 5, %(count)s, %(count)s)
            RETURNING id
            """,
            {"screen_id": screen[0], "now": NOW_UTC, "definition": Jsonb({}), "count": len(members)},
        ).fetchone()
        assert result is not None
        for position, member in enumerate(members, start=1):
            connection.execute(
                """
                INSERT INTO screen_result_row (screen_result_id, position, symbol, exchange, currency, values)
                VALUES (%(id)s, %(position)s, %(symbol)s, %(exchange)s, %(currency)s, %(values)s)
                """,
                {
                    "id": result[0],
                    "position": position,
                    "symbol": member.symbol,
                    "exchange": member.exchange,
                    "currency": member.currency,
                    "values": Jsonb({}),
                },
            )
    return int(result[0])


@pytest.mark.anyio
async def test_a_list_from_a_screen_result_takes_all_its_rows_and_has_the_survivorship_bias_warning(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    save_universe_test_data(database_url)
    screen_result_id = save_screen_result(database_url, [AAA, CCC])
    saved = await save_test_strategy_version(web_client)

    response = await web_client.post(
        "/api/backtests",
        json=make_universe_request(
            saved["strategy_version_id"], universe_kind="list", screen_result_id=screen_result_id
        ),
    )

    assert response.status_code == 201
    assert response.json()["survivorship_bias"] is True
    assert read_universe_members(database_url, response.json()["id"]) == [
        (f"{RANGE_START_UTC:%Y-%m-%d}", "AAA", "NASDAQ"),
        (f"{RANGE_START_UTC:%Y-%m-%d}", "CCC", "ARCA"),
    ]


@pytest.mark.anyio
async def test_a_list_from_a_screen_result_takes_only_the_given_symbols(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    save_universe_test_data(database_url)
    screen_result_id = save_screen_result(database_url, [AAA, CCC])
    saved = await save_test_strategy_version(web_client)

    response = await web_client.post(
        "/api/backtests",
        json=make_universe_request(
            saved["strategy_version_id"], universe_kind="list", screen_result_id=screen_result_id, symbols=["CCC"]
        ),
    )

    assert response.status_code == 201
    assert read_universe_members(database_url, response.json()["id"]) == [
        (f"{RANGE_START_UTC:%Y-%m-%d}", "CCC", "ARCA")
    ]


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("fields", "reason"),
    [
        pytest.param({"screen_result_id": 999_999}, "999999", id="missing screen result"),
        pytest.param({"symbols": ["ZZZ"]}, "ZZZ", id="symbol not in the screen result"),
        pytest.param({"symbols": ["AAA"], "screen_result_id": None}, "symbols", id="symbols without screen result"),
    ],
)
async def test_rejects_a_screen_result_list_that_is_not_valid(
    web_client: httpx.AsyncClient, database_url: str, fields: dict[str, object], reason: str
) -> None:
    save_universe_test_data(database_url)
    screen_result_id = save_screen_result(database_url, [AAA, CCC])
    saved = await save_test_strategy_version(web_client)
    body: dict[str, object] = {"screen_result_id": screen_result_id, **fields}
    if body["screen_result_id"] is None:
        del body["screen_result_id"]
        body["instruments"] = [{"symbol": "AAA", "exchange": "NASDAQ", "currency": "USD"}]

    response = await web_client.post(
        "/api/backtests", json=make_universe_request(saved["strategy_version_id"], universe_kind="list", **body)
    )

    assert response.status_code == 422
    assert reason in str(response.json()["detail"])
    assert await count_backtests(web_client) == 0
