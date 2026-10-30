"""The start route of a multi-instrument backtest: the universe kinds, their checks, and the members of each universe
period (docs/architecture/backtest.md section 10.10.6)."""

from dataclasses import replace

import httpx
import psycopg
import pytest

from atrade.foundation.instrument import Instrument
from tests.backtest.real_runner import save_test_bars
from tests.backtest.test_backtest_routes import make_backtest_request, save_test_strategy_version
from tests.backtest.universe_data import (
    AAA,
    BBB,
    CCC,
    RANGE_START_UTC,
    SECOND_QUARTER_START_UTC,
    make_universe_request,
    save_universe_test_data,
    to_instrument_body,
)


def read_universe_members(database_url: str, backtest_id: int) -> list[tuple[str, str, str]]:
    with psycopg.connect(database_url) as connection:
        rows = connection.execute(
            """
            SELECT period_start_utc, symbol, exchange FROM backtest_universe_member
            WHERE backtest_id = %s ORDER BY period_start_utc, symbol
            """,
            (backtest_id,),
        ).fetchall()
    return [(f"{row[0]:%Y-%m-%d}", row[1], row[2]) for row in rows]


async def count_backtests(web_client: httpx.AsyncClient) -> int:
    return len((await web_client.get("/api/backtests")).json())


@pytest.mark.anyio
async def test_a_request_without_universe_kind_is_a_single_instrument_backtest(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    save_test_bars(database_url)
    saved = await save_test_strategy_version(web_client)

    response = await web_client.post("/api/backtests", json=make_backtest_request(saved["strategy_version_id"]))

    assert response.status_code == 201
    backtest = response.json()
    assert backtest["universe_kind"] == "single"
    assert backtest["universe_top_n"] is None
    assert (backtest["symbol"], backtest["exchange"], backtest["currency"]) == ("BTEST", "ARCA", "USD")
    assert read_universe_members(database_url, backtest["id"]) == []


@pytest.mark.anyio
async def test_a_rule_backtest_records_the_members_of_each_quarter_in_the_range(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    save_universe_test_data(database_url)
    saved = await save_test_strategy_version(web_client)

    response = await web_client.post(
        "/api/backtests", json=make_universe_request(saved["strategy_version_id"], universe_kind="rule", top_n=2)
    )

    assert response.status_code == 201
    backtest = response.json()
    assert backtest["universe_kind"] == "rule"
    assert backtest["universe_top_n"] == 2
    assert (backtest["symbol"], backtest["exchange"], backtest["currency"]) == (None, None, "USD")
    # The first period starts at the range start, inside the first quarter.
    assert read_universe_members(database_url, backtest["id"]) == [
        (f"{RANGE_START_UTC:%Y-%m-%d}", "AAA", "NASDAQ"),
        (f"{RANGE_START_UTC:%Y-%m-%d}", "BBB", "NYSE"),
        (f"{SECOND_QUARTER_START_UTC:%Y-%m-%d}", "BBB", "NYSE"),
        (f"{SECOND_QUARTER_START_UTC:%Y-%m-%d}", "CCC", "ARCA"),
    ]


@pytest.mark.anyio
async def test_a_rule_backtest_takes_only_the_top_n_members(web_client: httpx.AsyncClient, database_url: str) -> None:
    save_universe_test_data(database_url)
    saved = await save_test_strategy_version(web_client)

    response = await web_client.post(
        "/api/backtests", json=make_universe_request(saved["strategy_version_id"], universe_kind="rule", top_n=1)
    )

    assert response.status_code == 201
    assert [symbol for _, symbol, _ in read_universe_members(database_url, response.json()["id"])] == ["AAA", "BBB"]


@pytest.mark.anyio
async def test_a_list_backtest_has_one_period_from_the_range_start(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    save_universe_test_data(database_url)
    saved = await save_test_strategy_version(web_client)
    instruments = [to_instrument_body(AAA), to_instrument_body(CCC)]

    response = await web_client.post(
        "/api/backtests",
        json=make_universe_request(saved["strategy_version_id"], universe_kind="list", instruments=instruments),
    )

    assert response.status_code == 201
    assert response.json()["universe_kind"] == "list"
    assert read_universe_members(database_url, response.json()["id"]) == [
        (f"{RANGE_START_UTC:%Y-%m-%d}", "AAA", "NASDAQ"),
        (f"{RANGE_START_UTC:%Y-%m-%d}", "CCC", "ARCA"),
    ]


HKD_INSTRUMENT = Instrument(symbol="700", exchange="SEHK", currency="HKD")


@pytest.mark.anyio
@pytest.mark.parametrize(
    "universe",
    [
        pytest.param({"universe_kind": "sector"}, id="unknown kind"),
        pytest.param({"universe_kind": "screen", "screen_id": 1}, id="screen is not in this slice"),
        pytest.param({"universe_kind": "rule", "top_n": 0}, id="top_n 0"),
        pytest.param({"universe_kind": "rule", "top_n": 501}, id="top_n 501"),
        pytest.param({"universe_kind": "rule"}, id="rule without top_n"),
        pytest.param({"universe_kind": "list", "instruments": []}, id="empty list"),
        pytest.param({"universe_kind": "list"}, id="list without instruments"),
        pytest.param(
            {"universe_kind": "list", "instruments": [to_instrument_body(AAA), to_instrument_body(HKD_INSTRUMENT)]},
            id="2 currencies",
        ),
        pytest.param({"universe_kind": "rule", "top_n": 2, "bar_period": "5-MINUTE"}, id="5-minute bars"),
        pytest.param(
            {"universe_kind": "list", "instruments": [to_instrument_body(AAA)], "bar_period": "1-MINUTE"},
            id="1-minute bars",
        ),
        pytest.param({"universe_kind": "single"}, id="single without an instrument"),
        pytest.param({"universe_kind": "single", **to_instrument_body(AAA), "top_n": 2}, id="single with top_n"),
        pytest.param(
            {"universe_kind": "rule", "top_n": 2, "instruments": [to_instrument_body(AAA)]}, id="rule with instruments"
        ),
        pytest.param({"universe_kind": "rule", "top_n": 2, **to_instrument_body(AAA)}, id="rule with an instrument"),
        pytest.param(
            {"universe_kind": "list", "top_n": 2, "instruments": [to_instrument_body(AAA)]}, id="list with top_n"
        ),
        pytest.param(
            {
                "universe_kind": "list",
                "instruments": [to_instrument_body(AAA), to_instrument_body(replace(AAA, exchange="NYSE"))],
            },
            id="1 symbol on 2 exchanges",
        ),
    ],
)
async def test_rejects_a_universe_that_is_not_valid_and_adds_no_row(
    web_client: httpx.AsyncClient, database_url: str, universe: dict[str, object]
) -> None:
    save_universe_test_data(database_url)
    saved = await save_test_strategy_version(web_client)

    response = await web_client.post(
        "/api/backtests", json=make_universe_request(saved["strategy_version_id"], **universe)
    )

    assert response.status_code == 422
    assert await count_backtests(web_client) == 0


@pytest.mark.anyio
async def test_rejects_a_rule_backtest_when_no_universe_data_covers_the_range(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    save_test_bars(database_url)
    saved = await save_test_strategy_version(web_client)

    response = await web_client.post(
        "/api/backtests", json=make_universe_request(saved["strategy_version_id"], universe_kind="rule", top_n=500)
    )

    assert response.status_code == 422
    assert "universe" in response.json()["detail"]
    assert await count_backtests(web_client) == 0


@pytest.mark.anyio
async def test_rejects_a_list_backtest_when_no_member_has_a_saved_bar_in_the_range(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    save_test_bars(database_url)
    saved = await save_test_strategy_version(web_client)

    response = await web_client.post(
        "/api/backtests",
        json=make_universe_request(
            saved["strategy_version_id"], universe_kind="list", instruments=[to_instrument_body(BBB)]
        ),
    )

    assert response.status_code == 422
    assert await count_backtests(web_client) == 0
