"""The start route of a `screen` universe: the point-in-time rerun of a screen (docs/architecture/backtest.md section
10.10.6, docs/architecture/screen.md section 24.9)."""

from typing import Any

import httpx
import pytest

from tests.backtest.test_backtest_routes import save_test_strategy_version
from tests.backtest.test_universe_backtest_routes import count_backtests, read_universe_members
from tests.backtest.universe_data import make_universe_request, save_universe_test_data
from tests.screen.test_screen_run_routes import create_screen, make_definition


async def start_screen_backtest(
    web_client: httpx.AsyncClient, strategy_version_id: int, **universe: object
) -> httpx.Response:
    return await web_client.post(
        "/api/backtests", json=make_universe_request(strategy_version_id, universe_kind="screen", **universe)
    )


@pytest.mark.anyio
async def test_a_screen_backtest_saves_a_copy_of_the_screen_and_the_quarter_period_by_default(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    save_universe_test_data(database_url)
    definition = make_definition(start="quarter_universe")
    screen_id = await create_screen(web_client, definition)
    saved = await save_test_strategy_version(web_client)

    response = await start_screen_backtest(web_client, saved["strategy_version_id"], screen_id=screen_id)

    assert response.status_code == 201, response.text
    backtest = response.json()
    assert backtest["universe_kind"] == "screen"
    assert (backtest["symbol"], backtest["exchange"], backtest["currency"]) == (None, None, "USD")
    assert backtest["universe_rebalance_period"] == "quarter"
    assert backtest["universe_screen"] == {
        "screen_id": screen_id,
        "name": "quarter_universe US",
        "market": "US",
        "definition": definition,
    }
    # The US universe of each quarter is point in time, and the range is after the Databento history start.
    assert backtest["survivorship_bias"] is False
    # The child writes the members of each period: the start route does not run the screen.
    assert read_universe_members(database_url, backtest["id"]) == []


@pytest.mark.anyio
async def test_a_later_change_or_delete_of_the_screen_does_not_change_the_backtest(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    save_universe_test_data(database_url)
    definition = make_definition(start="quarter_universe")
    screen_id = await create_screen(web_client, definition)
    saved = await save_test_strategy_version(web_client)
    started = (
        await start_screen_backtest(
            web_client, saved["strategy_version_id"], screen_id=screen_id, rebalance_period="month"
        )
    ).json()

    changed = await web_client.put(
        f"/api/screens/{screen_id}",
        json={"name": "Changed", "definition": make_definition(start="watchlist")},
    )
    assert changed.status_code == 200, changed.text
    after_change: dict[str, Any] = (await web_client.get(f"/api/backtests/{started['id']}")).json()
    assert (await web_client.delete(f"/api/screens/{screen_id}")).status_code == 204
    after_delete: dict[str, Any] = (await web_client.get(f"/api/backtests/{started['id']}")).json()

    assert started["universe_rebalance_period"] == "month"
    for backtest in (after_change, after_delete):
        assert backtest["universe_screen"] == started["universe_screen"]
        assert backtest["universe_rebalance_period"] == "month"


@pytest.mark.anyio
async def test_a_screen_that_starts_from_the_watchlist_has_the_survivorship_bias_warning(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    save_universe_test_data(database_url)
    screen_id = await create_screen(web_client, make_definition(start="watchlist"))
    saved = await save_test_strategy_version(web_client)

    response = await start_screen_backtest(web_client, saved["strategy_version_id"], screen_id=screen_id)

    assert response.status_code == 201, response.text
    assert response.json()["survivorship_bias"] is True


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("fields", "reason"),
    [
        pytest.param({"screen_id": 999_999}, "999999", id="missing screen"),
        pytest.param({}, "screen_id", id="no screen"),
        pytest.param({"rebalance_period": "week"}, None, id="unknown period"),
        pytest.param({"top_n": 5}, "top_n", id="field of another kind"),
    ],
)
async def test_rejects_a_screen_universe_that_is_not_valid(
    web_client: httpx.AsyncClient, database_url: str, fields: dict[str, object], reason: str | None
) -> None:
    save_universe_test_data(database_url)
    screen_id = await create_screen(web_client, make_definition(start="quarter_universe"))
    saved = await save_test_strategy_version(web_client)
    body: dict[str, object] = {"screen_id": screen_id, **fields} if fields else {}

    response = await start_screen_backtest(web_client, saved["strategy_version_id"], **body)

    assert response.status_code == 422
    if reason is not None:
        assert reason in str(response.json()["detail"])
    assert await count_backtests(web_client) == 0


@pytest.mark.anyio
@pytest.mark.parametrize("fields", [{"screen_id": 1}, {"rebalance_period": "month"}])
async def test_a_list_universe_does_not_take_the_screen_fields(
    web_client: httpx.AsyncClient, database_url: str, fields: dict[str, object]
) -> None:
    save_universe_test_data(database_url)
    saved = await save_test_strategy_version(web_client)

    response = await web_client.post(
        "/api/backtests",
        json=make_universe_request(
            saved["strategy_version_id"],
            universe_kind="list",
            instruments=[{"symbol": "AAA", "exchange": "NASDAQ", "currency": "USD"}],
            **fields,
        ),
    )

    assert response.status_code == 422
    assert next(iter(fields)) in str(response.json()["detail"])
