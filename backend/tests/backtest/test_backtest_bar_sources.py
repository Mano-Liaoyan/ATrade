"""The bar sources of a backtest: the source order of the request, the saved bar counts, and the survivorship bias
flag (docs/architecture/backtest.md section 10.12)."""

from datetime import UTC, datetime, timedelta

import httpx
import psycopg
import pytest
from psycopg import sql

from atrade.foundation.instrument import Instrument
from atrade.strategy.strategy_template import STRATEGY_TEMPLATE
from tests.backtest.real_runner import (
    TEST_STRATEGY_FILE,
    run_backtest_runner,
    save_test_bars,
    start_backtest,
    wait_for_final_status,
)
from tests.backtest.test_backtest_routes import make_backtest_request, save_test_strategy_version
from tests.fakes.clock import FixedClock
from tests.saved_ranges import save_ibkr_saved_range

BTEST = Instrument(symbol="BTEST", exchange="ARCA", currency="USD")


def copy_test_bars_to_databento(database_url: str, start_utc: datetime, end_utc: datetime) -> None:
    """Copies all saved IBKR test bars to databento_bar, and saves one Databento range."""
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute("INSERT INTO databento_bar SELECT * FROM ibkr_bar")
        connection.execute(
            """
            INSERT INTO databento_bar_saved_range (symbol, exchange, currency, bar_period, start_utc, end_utc)
            VALUES ('BTEST', 'ARCA', 'USD', '1-DAY', %(start_utc)s, %(end_utc)s)
            """,
            {"start_utc": start_utc, "end_utc": end_utc},
        )


@pytest.mark.anyio
async def test_backtest_without_a_source_order_uses_the_global_source_order(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    save_test_bars(database_url)
    saved = await save_test_strategy_version(web_client)
    changed = await web_client.put("/api/market-data/source-order", json={"source_order": ["databento", "ibkr"]})
    assert changed.status_code == 200

    response = await web_client.post("/api/backtests", json=make_backtest_request(saved["strategy_version_id"]))

    assert response.status_code == 201
    detail = (await web_client.get(f"/api/backtests/{response.json()['id']}")).json()
    assert detail["source_order"] == ["databento", "ibkr"]
    assert detail["bar_count_by_source"] is None


@pytest.mark.anyio
async def test_backtest_keeps_the_source_order_of_its_request(web_client: httpx.AsyncClient, database_url: str) -> None:
    save_test_bars(database_url)
    saved = await save_test_strategy_version(web_client)
    request = {**make_backtest_request(saved["strategy_version_id"]), "source_order": ["databento", "ibkr"]}

    response = await web_client.post("/api/backtests", json=request)

    assert response.status_code == 201
    assert response.json()["source_order"] == ["databento", "ibkr"]
    global_order = (await web_client.get("/api/market-data/source-order")).json()
    assert global_order == {"source_order": ["ibkr", "databento"]}


@pytest.mark.anyio
@pytest.mark.parametrize("source_order", [[], ["ibkr", "ibkr"], ["ibkr", "yahoo"]])
async def test_rejects_a_source_order_that_is_empty_has_a_value_2_times_or_an_unknown_value(
    web_client: httpx.AsyncClient, database_url: str, source_order: list[str]
) -> None:
    save_test_bars(database_url)
    saved = await save_test_strategy_version(web_client)
    request = {**make_backtest_request(saved["strategy_version_id"]), "source_order": source_order}

    response = await web_client.post("/api/backtests", json=request)

    assert response.status_code == 422
    assert (await web_client.get("/api/backtests")).json() == []


@pytest.mark.anyio
async def test_start_route_finds_the_saved_bars_through_the_source_order_of_the_request(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    # Databento saved the range without bars. With Databento first, the range has no bar.
    save_test_bars(database_url)
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            """
            INSERT INTO databento_bar_saved_range (symbol, exchange, currency, bar_period, start_utc, end_utc)
            VALUES ('BTEST', 'ARCA', 'USD', '1-DAY', '2026-01-01T00:00:00Z', '2026-05-01T00:00:00Z')
            """
        )
    saved = await save_test_strategy_version(web_client)
    request = {**make_backtest_request(saved["strategy_version_id"]), "source_order": ["databento", "ibkr"]}

    response = await web_client.post("/api/backtests", json=request)

    assert response.status_code == 422
    assert response.json()["detail"].startswith("There are no saved 1 day bars of BTEST / ARCA / USD")


def insert_backtest_row(
    database_url: str, strategy_version_id: int, instrument: Instrument, start_utc: datetime
) -> int:
    """A backtest row without the columns of section 10.12, like a row from before the migration."""
    with psycopg.connect(database_url, autocommit=True) as connection:
        row = connection.execute(
            """
            INSERT INTO backtest (strategy_version_id, symbol, exchange, currency, bar_period, start_utc, end_utc,
                paper_capital_usd, status, created_at_utc)
            VALUES (%(strategy_version_id)s, %(symbol)s, %(exchange)s, %(currency)s, '1-DAY', %(start_utc)s,
                %(end_utc)s, 10000, 'queued', %(start_utc)s)
            RETURNING id
            """,
            {
                "strategy_version_id": strategy_version_id,
                "symbol": instrument.symbol,
                "exchange": instrument.exchange,
                "currency": instrument.currency,
                "start_utc": start_utc,
                "end_utc": start_utc + timedelta(days=30),
            },
        ).fetchone()
    assert row is not None
    return int(row[0])


@pytest.mark.anyio
async def test_backtest_from_before_the_bar_sources_has_no_source_order_and_no_bar_counts(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    saved = await save_test_strategy_version(web_client)
    backtest_id = insert_backtest_row(
        database_url, saved["strategy_version_id"], BTEST, datetime(2026, 3, 1, tzinfo=UTC)
    )

    detail = (await web_client.get(f"/api/backtests/{backtest_id}")).json()

    assert detail["source_order"] is None
    assert detail["bar_count_by_source"] is None


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("instrument", "start_utc", "survivorship_bias"),
    [
        (Instrument(symbol="700", exchange="SEHK", currency="HKD"), datetime(2026, 3, 1, tzinfo=UTC), True),
        (BTEST, datetime(2018, 4, 30, tzinfo=UTC), True),
        (BTEST, datetime(2018, 5, 1, tzinfo=UTC), False),
    ],
)
async def test_hk_backtests_and_us_backtests_before_the_databento_history_have_survivorship_bias(
    web_client: httpx.AsyncClient,
    database_url: str,
    instrument: Instrument,
    start_utc: datetime,
    survivorship_bias: bool,
) -> None:
    saved = await save_test_strategy_version(web_client)
    backtest_id = insert_backtest_row(database_url, saved["strategy_version_id"], instrument, start_utc)

    detail = (await web_client.get(f"/api/backtests/{backtest_id}")).json()
    listed = (await web_client.get("/api/backtests")).json()

    assert detail["survivorship_bias"] is survivorship_bias
    assert listed[0]["survivorship_bias"] is survivorship_bias


@pytest.mark.anyio
async def test_backtest_reads_each_part_of_the_range_from_the_first_bar_source_that_saved_it(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    # The test bars are 2026-03-02 to 2026-03-21. IBKR saved only up to 2026-03-11: 9 bars. Databento saved all of
    # them, so it gives the other 11 bars. Both have the same bars, so the result is the result of the bar file.
    save_test_bars(database_url)
    copy_test_bars_to_databento(database_url, datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 5, 1, tzinfo=UTC))
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute("DELETE FROM ibkr_bar_saved_range")
        save_ibkr_saved_range(
            connection, BTEST, "1-DAY", datetime(2026, 3, 1, tzinfo=UTC), datetime(2026, 3, 11, tzinfo=UTC)
        )
    backtest_id = await start_backtest(web_client, TEST_STRATEGY_FILE.read_text())

    async with run_backtest_runner(web_client, database_url, clock, timeout_seconds=60):
        backtest = await wait_for_final_status(web_client, backtest_id)

    assert backtest["status"] == "finished", backtest["error_message"]
    assert backtest["source_order"] == ["ibkr", "databento"]
    assert backtest["bar_count_by_source"] == {"ibkr": 9, "databento": 11}
    assert backtest["metrics"]["final_equity_usd"] == "10160.00"


@pytest.mark.anyio
async def test_look_back_bars_follow_the_source_order_of_the_backtest(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    # Before the start (2026-03-01), IBKR has 59 bars at 500 and Databento has 59 bars at 50. Databento saved only
    # the look-back range, so the range bars come from IBKR. With Databento first, the 20-bar average is 50 and the
    # template buys on the first bar of the range (close 100). With the IBKR look-back bars, the average is 500.
    save_test_bars(database_url)
    look_back_days = [datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=index) for index in range(59)]
    with psycopg.connect(database_url, autocommit=True) as connection, connection.cursor() as cursor:
        for table, close in (("ibkr_bar", 500), ("databento_bar", 50)):
            cursor.executemany(
                sql.SQL("""
                INSERT INTO {} (symbol, exchange, currency, bar_period, start_utc, open, high, low, close, volume)
                VALUES ('BTEST', 'ARCA', 'USD', '1-DAY', %(start_utc)s, %(close)s, %(close)s, %(close)s, %(close)s,
                    1000)
                """).format(sql.Identifier(table)),
                [{"start_utc": start_utc, "close": close} for start_utc in look_back_days],
            )
        connection.execute(
            """
            INSERT INTO databento_bar_saved_range (symbol, exchange, currency, bar_period, start_utc, end_utc)
            VALUES ('BTEST', 'ARCA', 'USD', '1-DAY', '2026-01-01T00:00:00Z', '2026-03-01T00:00:00Z')
            """
        )
    strategy = (await web_client.post("/api/strategies", json={"name": "Template"})).json()
    version = (
        await web_client.post(f"/api/strategies/{strategy['id']}/versions", json={"code": STRATEGY_TEMPLATE})
    ).json()
    request = {**make_backtest_request(version["id"]), "source_order": ["databento", "ibkr"]}
    backtest_id = (await web_client.post("/api/backtests", json=request)).json()["id"]

    async with run_backtest_runner(web_client, database_url, clock, timeout_seconds=60):
        backtest = await wait_for_final_status(web_client, backtest_id)

    assert backtest["status"] == "finished", backtest["error_message"]
    assert backtest["bar_count_by_source"] == {"databento": 0, "ibkr": 20}
    assert backtest["trades"][0]["time_utc"] == "2026-03-03T00:00:00Z"
    assert backtest["trades"][0]["price_usd"] == "100.00"
