"""Forward test start, stop, and list through the HTTP routes (docs/architecture.md sections 12.1-12.4).

The Web process writes only the desired state. The worker (test_forward_test_worker.py) writes the actual state.
"""

from pathlib import Path
from typing import Any

import httpx
import psycopg
import pytest

from atrade.app.web import create_web_app
from atrade.foundation.settings import Settings
from tests.fakes.clock import FixedClock
from tests.fakes.ibkr import FakeGatewayConnection, make_balance_values

TEST_STRATEGY_FILE = Path(__file__).parents[1] / "backtest" / "strategies" / "buy_and_sell_by_bar_count.py"
FORWARD_TESTS_PATH = "/api/forward-tests"
FAKE_ACCOUNT_ID = "DU1234567"

type JsonObject = dict[str, Any]


async def save_test_strategy_version(web_client: httpx.AsyncClient) -> int:
    # A new strategy has version 1 from the template. The test strategy becomes version 2.
    strategy = (await web_client.post("/api/strategies", json={"name": "Bar count"})).json()
    code = TEST_STRATEGY_FILE.read_text()
    version = (await web_client.post(f"/api/strategies/{strategy['id']}/versions", json={"code": code})).json()
    return version["id"]


def make_start_request(
    strategy_version_id: int, *, symbol: str = "AAPL", allocated_capital_usd: str = "10000"
) -> JsonObject:
    return {
        "strategy_version_id": strategy_version_id,
        "symbol": symbol,
        "exchange": "NASDAQ",
        "currency": "USD",
        "bar_period": "1-MINUTE",
        "allocated_capital_usd": allocated_capital_usd,
    }


def make_paper_gateway(net_liquidation_usd: str = "100000") -> FakeGatewayConnection:
    gateway_connection = FakeGatewayConnection(managed_accounts=[FAKE_ACCOUNT_ID])
    gateway_connection.connected = True
    gateway_connection.account_values = make_balance_values(
        FAKE_ACCOUNT_ID, net_liquidation_usd=net_liquidation_usd, cash_usd=net_liquidation_usd
    )
    return gateway_connection


@pytest.mark.anyio
async def test_starts_a_forward_test_with_the_lowest_free_client_id(web_client: httpx.AsyncClient) -> None:
    strategy_version_id = await save_test_strategy_version(web_client)

    response = await web_client.post(FORWARD_TESTS_PATH, json=make_start_request(strategy_version_id))

    assert response.status_code == 201
    forward_test = response.json()
    assert forward_test["strategy_version_id"] == strategy_version_id
    assert forward_test["strategy_name"] == "Bar count"
    assert forward_test["version_number"] == 2
    assert forward_test["symbol"] == "AAPL"
    assert forward_test["bar_period"] == "1-MINUTE"
    assert forward_test["desired_state"] == "running"
    assert forward_test["status"] == "starting"
    assert forward_test["client_id"] == 10
    assert forward_test["start_balance_usd"] is None
    assert forward_test["allocated_capital_usd"] == "10000"
    assert forward_test["created_at_utc"] == "2026-01-02T03:04:05Z"


@pytest.mark.anyio
async def test_lists_forward_tests_newest_first(web_client: httpx.AsyncClient) -> None:
    strategy_version_id = await save_test_strategy_version(web_client)
    await web_client.post(FORWARD_TESTS_PATH, json=make_start_request(strategy_version_id, symbol="AAPL"))
    await web_client.post(FORWARD_TESTS_PATH, json=make_start_request(strategy_version_id, symbol="MSFT"))

    response = await web_client.get(FORWARD_TESTS_PATH)

    assert response.status_code == 200
    assert [(item["symbol"], item["client_id"]) for item in response.json()] == [("MSFT", 11), ("AAPL", 10)]


@pytest.mark.anyio
async def test_the_list_reads_all_forward_tests_with_a_fixed_number_of_connections(
    web_client: httpx.AsyncClient, database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # /ws/forward-tests reads the list every 2 seconds for each open page. Connections for each row made the first
    # message of a page late by many seconds under the load of the e2e suite.
    first_version_id = await save_test_strategy_version(web_client)
    template_strategy = (await web_client.post("/api/strategies", json={"name": "Template"})).json()
    template_version_id = (await web_client.get(f"/api/strategies/{template_strategy['id']}")).json()["versions"][0][
        "id"
    ]
    aapl = (await web_client.post(FORWARD_TESTS_PATH, json=make_start_request(first_version_id, symbol="AAPL"))).json()
    await web_client.post(FORWARD_TESTS_PATH, json=make_start_request(template_version_id, symbol="MSFT"))
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            """
            INSERT INTO forward_test_interruption (forward_test_id, reason, started_at_utc)
            VALUES (%(id)s, 'crash', '2026-01-02T03:05:00Z')
            """,
            {"id": aapl["id"]},
        )
    connect = psycopg.AsyncConnection.connect
    connection_count = 0

    async def count_connection(*args: Any, **kwargs: Any) -> psycopg.AsyncConnection:
        nonlocal connection_count
        connection_count += 1
        return await connect(*args, **kwargs)

    monkeypatch.setattr(psycopg.AsyncConnection, "connect", count_connection)

    response = await web_client.get(FORWARD_TESTS_PATH)

    listed = [(item["symbol"], item["strategy_name"], len(item["interruptions"])) for item in response.json()]
    assert listed == [("MSFT", "Template", 0), ("AAPL", "Bar count", 1)]
    # The forward tests, the strategy versions, and the "Split check needed" instruments.
    assert connection_count == 4


@pytest.mark.anyio
async def test_refuses_start_when_no_client_id_is_free(web_client: httpx.AsyncClient) -> None:
    strategy_version_id = await save_test_strategy_version(web_client)
    # The default client ID range 10-13 allows 4 forward tests at the same time.
    for symbol in ["AAPL", "MSFT", "AMZN", "ABNB"]:
        await web_client.post(FORWARD_TESTS_PATH, json=make_start_request(strategy_version_id, symbol=symbol))

    response = await web_client.post(FORWARD_TESTS_PATH, json=make_start_request(strategy_version_id, symbol="AMD"))

    assert response.status_code == 409
    assert response.json() == {
        "detail": "limit of running forward tests reached",
        "forward_test_id": None,
        "unallocated_usd": None,
    }


@pytest.mark.anyio
async def test_two_forward_tests_can_run_on_the_same_instrument(web_client: httpx.AsyncClient) -> None:
    strategy_version_id = await save_test_strategy_version(web_client)
    first = await web_client.post(FORWARD_TESTS_PATH, json=make_start_request(strategy_version_id))

    second = await web_client.post(FORWARD_TESTS_PATH, json=make_start_request(strategy_version_id))

    assert (first.status_code, second.status_code) == (201, 201)
    assert (first.json()["client_id"], second.json()["client_id"]) == (10, 11)


@pytest.mark.anyio
async def test_refuses_an_allocated_capital_larger_than_the_unallocated_amount(
    web_client: httpx.AsyncClient,
) -> None:
    strategy_version_id = await save_test_strategy_version(web_client)
    await web_client.post(
        FORWARD_TESTS_PATH, json=make_start_request(strategy_version_id, allocated_capital_usd="78750")
    )

    response = await web_client.post(
        FORWARD_TESTS_PATH, json=make_start_request(strategy_version_id, allocated_capital_usd="30000")
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "The allocated capital 30,000.00 USD is larger than the unallocated 21,250.00 USD.",
        "forward_test_id": None,
        "unallocated_usd": "21250",
    }


@pytest.mark.parametrize("allocated_capital_usd", ["0", "-5"])
@pytest.mark.anyio
async def test_refuses_an_allocated_capital_that_is_not_larger_than_0(
    web_client: httpx.AsyncClient, allocated_capital_usd: str
) -> None:
    strategy_version_id = await save_test_strategy_version(web_client)

    response = await web_client.post(
        FORWARD_TESTS_PATH, json=make_start_request(strategy_version_id, allocated_capital_usd=allocated_capital_usd)
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_the_capital_route_gives_the_allocated_and_the_unallocated_amounts(
    web_client: httpx.AsyncClient,
) -> None:
    strategy_version_id = await save_test_strategy_version(web_client)
    await web_client.post(
        FORWARD_TESTS_PATH, json=make_start_request(strategy_version_id, allocated_capital_usd="30000")
    )

    response = await web_client.get(f"{FORWARD_TESTS_PATH}/capital")

    assert response.status_code == 200
    assert response.json() == {"net_liquidation_usd": "100000", "allocated_usd": "30000", "unallocated_usd": "70000"}


@pytest.mark.anyio
async def test_without_a_passed_check_the_capital_is_unknown_and_the_start_is_refused(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    settings = Settings(database_url=database_url, frontend_build_dir=frontend_build_dir)
    app = create_web_app(settings=settings, clock=clock, gateway_connection=make_paper_gateway())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        strategy_version_id = await save_test_strategy_version(client)
        capital = await client.get(f"{FORWARD_TESTS_PATH}/capital")
        start = await client.post(FORWARD_TESTS_PATH, json=make_start_request(strategy_version_id))

    assert capital.json() == {"net_liquidation_usd": None, "allocated_usd": None, "unallocated_usd": None}
    assert start.status_code == 409
    assert start.json()["detail"].startswith("The paper account check failed:")


@pytest.mark.anyio
async def test_refuses_the_start_without_a_net_liquidation_value_in_usd(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    settings = Settings(
        database_url=database_url, frontend_build_dir=frontend_build_dir, ibkr_account_id=FAKE_ACCOUNT_ID
    )
    gateway_connection = make_paper_gateway()
    gateway_connection.account_values = []
    app = create_web_app(settings=settings, clock=clock, gateway_connection=gateway_connection)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        strategy_version_id = await save_test_strategy_version(client)
        capital = await client.get(f"{FORWARD_TESTS_PATH}/capital")
        start = await client.post(FORWARD_TESTS_PATH, json=make_start_request(strategy_version_id))

    assert capital.json() == {"net_liquidation_usd": None, "allocated_usd": None, "unallocated_usd": None}
    assert start.status_code == 409
    assert start.json()["detail"].startswith("The paper account has no NetLiquidation value in USD.")


@pytest.mark.anyio
async def test_refuses_start_of_a_missing_strategy_version(web_client: httpx.AsyncClient) -> None:
    response = await web_client.post(FORWARD_TESTS_PATH, json=make_start_request(999))

    assert response.status_code == 422
    assert response.json() == {"detail": "Strategy version 999 does not exist."}


@pytest.mark.anyio
async def test_refuses_a_bar_period_that_ib_live_bars_do_not_support(web_client: httpx.AsyncClient) -> None:
    strategy_version_id = await save_test_strategy_version(web_client)
    request = {**make_start_request(strategy_version_id), "bar_period": "7-MINUTE"}

    response = await web_client.post(FORWARD_TESTS_PATH, json=request)

    assert response.status_code == 422


@pytest.mark.anyio
async def test_stop_writes_only_the_desired_state(web_client: httpx.AsyncClient) -> None:
    strategy_version_id = await save_test_strategy_version(web_client)
    forward_test = (await web_client.post(FORWARD_TESTS_PATH, json=make_start_request(strategy_version_id))).json()

    response = await web_client.post(f"{FORWARD_TESTS_PATH}/{forward_test['id']}/stop")

    assert response.status_code == 202
    [listed] = (await web_client.get(FORWARD_TESTS_PATH)).json()
    assert listed["desired_state"] == "stopped"
    # The worker writes the actual state and frees the client ID after the orders are cancelled.
    assert listed["status"] == "starting"
    assert listed["client_id"] == 10


@pytest.mark.anyio
async def test_stop_of_a_missing_forward_test_is_not_found(web_client: httpx.AsyncClient) -> None:
    response = await web_client.post(f"{FORWARD_TESTS_PATH}/999/stop")

    assert response.status_code == 404


@pytest.mark.anyio
async def test_uses_the_client_id_range_of_the_settings(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    settings = Settings(
        database_url=database_url,
        frontend_build_dir=frontend_build_dir,
        ibkr_account_id=FAKE_ACCOUNT_ID,
        forward_test_client_id_first=21,
        forward_test_client_id_last=21,
    )
    app = create_web_app(settings=settings, clock=clock, gateway_connection=make_paper_gateway())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        strategy_version_id = await save_test_strategy_version(client)
        first = await client.post(FORWARD_TESTS_PATH, json=make_start_request(strategy_version_id, symbol="AAPL"))
        second = await client.post(FORWARD_TESTS_PATH, json=make_start_request(strategy_version_id, symbol="MSFT"))

    assert first.json()["client_id"] == 21
    assert second.status_code == 409


@pytest.mark.anyio
async def test_the_end_time_is_optional_and_must_be_later_than_now(web_client: httpx.AsyncClient) -> None:
    strategy_version_id = await save_test_strategy_version(web_client)
    past = make_start_request(strategy_version_id) | {"end_time_utc": "2026-01-02T03:04:05Z"}
    without_time_zone = make_start_request(strategy_version_id) | {"end_time_utc": "2026-01-03T00:00:00"}
    later = make_start_request(strategy_version_id) | {"end_time_utc": "2026-01-03T09:30:00+08:00"}

    past_response = await web_client.post(FORWARD_TESTS_PATH, json=past)
    without_time_zone_response = await web_client.post(FORWARD_TESTS_PATH, json=without_time_zone)
    later_response = await web_client.post(FORWARD_TESTS_PATH, json=later)

    assert (past_response.status_code, past_response.json()["detail"]) == (422, "The end time must be later than now.")
    assert without_time_zone_response.status_code == 422
    assert later_response.status_code == 201
    # The database stores UTC (section 12.1).
    assert later_response.json()["end_time_utc"] == "2026-01-03T01:30:00Z"
    assert (later_response.json()["crash_count"], later_response.json()["interruptions"]) == (0, [])


def make_universe_request(strategy_version_id: int, universe: JsonObject, bar_period: str = "1-DAY") -> JsonObject:
    return {
        "strategy_version_id": strategy_version_id,
        "universe": universe,
        "bar_period": bar_period,
        "allocated_capital_usd": "10000",
    }


@pytest.mark.anyio
async def test_a_single_instrument_forward_test_has_the_universe_kind_single(web_client: httpx.AsyncClient) -> None:
    strategy_version_id = await save_test_strategy_version(web_client)
    universe = {"kind": "single", "symbol": "AAPL", "exchange": "NASDAQ", "currency": "USD"}

    response = await web_client.post(FORWARD_TESTS_PATH, json=make_universe_request(strategy_version_id, universe))

    assert response.status_code == 201
    assert response.json()["universe_kind"] == "single"
    assert response.json()["universe_top_n"] is None
    assert response.json()["symbol"] == "AAPL"


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("universe", "bar_period"),
    [
        ({"kind": "rule", "top_n": 10}, "1-MINUTE"),
        ({"kind": "list"}, "1-HOUR"),
        ({"kind": "rule", "top_n": 0}, "1-DAY"),
        ({"kind": "rule", "top_n": 501}, "1-DAY"),
    ],
)
async def test_refuses_a_multi_instrument_universe_with_a_wrong_bar_period_or_top_n(
    web_client: httpx.AsyncClient, universe: JsonObject, bar_period: str
) -> None:
    strategy_version_id = await save_test_strategy_version(web_client)

    response = await web_client.post(
        FORWARD_TESTS_PATH, json=make_universe_request(strategy_version_id, universe, bar_period)
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_refuses_a_watchlist_forward_test_with_an_empty_watchlist(web_client: httpx.AsyncClient) -> None:
    strategy_version_id = await save_test_strategy_version(web_client)

    response = await web_client.post(
        FORWARD_TESTS_PATH, json=make_universe_request(strategy_version_id, {"kind": "list"})
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "The watchlist has no instrument."


@pytest.mark.anyio
async def test_starts_a_watchlist_forward_test_and_records_the_members(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    strategy_version_id = await save_test_strategy_version(web_client)
    with psycopg.connect(database_url, autocommit=True) as connection:
        for symbol in ["AAPL", "MSFT"]:
            connection.execute(
                """
                INSERT INTO watchlist_instrument (symbol, exchange, currency, added_at_utc)
                VALUES (%(symbol)s, 'NASDAQ', 'USD', now())
                """,
                {"symbol": symbol},
            )

    response = await web_client.post(
        FORWARD_TESTS_PATH, json=make_universe_request(strategy_version_id, {"kind": "list"})
    )

    assert response.status_code == 201
    forward_test = response.json()
    assert forward_test["universe_kind"] == "list"
    assert forward_test["universe_top_n"] is None
    assert forward_test["symbol"] is None
    assert forward_test["client_id"] == 10
    assert read_recorded_members(database_url, forward_test["id"]) == [
        ("2026-01-01", "AAPL", "NASDAQ"),
        ("2026-01-01", "MSFT", "NASDAQ"),
    ]


def read_recorded_members(database_url: str, forward_test_id: int) -> list[tuple[str, str, str]]:
    with psycopg.connect(database_url) as connection:
        rows = connection.execute(
            """
            SELECT quarter_start_utc, symbol, exchange FROM forward_test_universe_member
            WHERE forward_test_id = %(id)s ORDER BY quarter_start_utc, symbol
            """,
            {"id": forward_test_id},
        ).fetchall()
    return [(f"{quarter_start_utc:%Y-%m-%d}", symbol, exchange) for quarter_start_utc, symbol, exchange in rows]


def save_us_universe_members(database_url: str, quarter_start_utc: str, symbols: list[str]) -> None:
    with psycopg.connect(database_url, autocommit=True) as connection:
        for rank, symbol in enumerate(symbols, start=1):
            connection.execute(
                """
                INSERT INTO us_universe_member (
                    quarter_start_utc, rank, symbol, exchange, currency, average_trading_value, last_ranking_day_utc
                )
                VALUES (%(quarter_start_utc)s, %(rank)s, %(symbol)s, 'NASDAQ', 'USD', 1000000, '2025-12-31T00:00:00Z')
                """,
                {"quarter_start_utc": quarter_start_utc, "rank": rank, "symbol": symbol},
            )


@pytest.mark.anyio
async def test_starts_a_top_n_forward_test_with_the_members_of_the_current_quarter(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    strategy_version_id = await save_test_strategy_version(web_client)
    save_us_universe_members(database_url, "2025-10-01T00:00:00Z", ["OLD"])
    # The clock is at 2026-01-02 03:04:05 UTC, the first trading day of the quarter.
    save_us_universe_members(database_url, "2026-01-02T00:00:00Z", ["NVDA", "AAPL", "MSFT"])

    response = await web_client.post(
        FORWARD_TESTS_PATH, json=make_universe_request(strategy_version_id, {"kind": "rule", "top_n": 2})
    )

    assert response.status_code == 201
    assert (response.json()["universe_kind"], response.json()["universe_top_n"]) == ("rule", 2)
    assert read_recorded_members(database_url, response.json()["id"]) == [
        ("2026-01-02", "AAPL", "NASDAQ"),
        ("2026-01-02", "NVDA", "NASDAQ"),
    ]


@pytest.mark.anyio
async def test_refuses_a_top_n_forward_test_without_a_stored_current_quarter(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    strategy_version_id = await save_test_strategy_version(web_client)
    save_us_universe_members(database_url, "2025-10-01T00:00:00Z", ["OLD"])

    response = await web_client.post(
        FORWARD_TESTS_PATH, json=make_universe_request(strategy_version_id, {"kind": "rule", "top_n": 2})
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "The US universe has no saved members for the quarter from 2026-01-01."


async def start_watchlist_forward_test(web_client: httpx.AsyncClient, database_url: str) -> JsonObject:
    strategy_version_id = await save_test_strategy_version(web_client)
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            """
            INSERT INTO watchlist_instrument (symbol, exchange, currency, added_at_utc)
            VALUES ('AAPL', 'NASDAQ', 'USD', now())
            """
        )
    response = await web_client.post(
        FORWARD_TESTS_PATH, json=make_universe_request(strategy_version_id, {"kind": "list"})
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.anyio
async def test_a_multi_instrument_forward_test_counts_in_the_limit_of_4_client_ids(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    watchlist_forward_test = await start_watchlist_forward_test(web_client, database_url)
    strategy_version_id = watchlist_forward_test["strategy_version_id"]
    for symbol in ["MSFT", "AMZN", "ABNB"]:
        await web_client.post(FORWARD_TESTS_PATH, json=make_start_request(strategy_version_id, symbol=symbol))

    response = await web_client.post(
        FORWARD_TESTS_PATH, json=make_universe_request(strategy_version_id, {"kind": "list"})
    )

    assert watchlist_forward_test["client_id"] == 10
    assert response.status_code == 409
    assert response.json()["detail"] == "limit of running forward tests reached"


@pytest.mark.anyio
async def test_the_detail_of_a_multi_instrument_forward_test_has_no_instrument(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    forward_test = await start_watchlist_forward_test(web_client, database_url)

    response = await web_client.get(f"{FORWARD_TESTS_PATH}/{forward_test['id']}")

    assert response.status_code == 200
    assert response.json()["forward_test"]["universe_kind"] == "list"
    assert response.json()["fills"] == []


@pytest.mark.anyio
async def test_refuses_a_same_period_backtest_of_a_multi_instrument_forward_test(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    forward_test = await start_watchlist_forward_test(web_client, database_url)

    response = await web_client.post(f"{FORWARD_TESTS_PATH}/{forward_test['id']}/same-period-backtests")

    assert response.status_code == 422
    assert response.json()["detail"] == "A multi-instrument forward test has no same-period backtest yet."
