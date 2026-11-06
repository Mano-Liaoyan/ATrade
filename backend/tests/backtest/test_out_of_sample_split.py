"""The in-sample and out-of-sample split of a backtest through the HTTP routes (docs/architecture/backtest.md
section 10.9.4): the share, the split time, the split metrics, and the out-of-sample use count."""

import httpx
import psycopg
import pytest

from tests.backtest.real_runner import run_backtest_runner, save_test_bars, wait_for_final_status
from tests.backtest.test_backtest_routes import TEST_STRATEGY_FILE, make_backtest_request, save_test_strategy_version
from tests.fakes.clock import FixedClock

# The saved bars of the range of `make_backtest_request` go from 2026-03-02 to 2026-03-22. 70 % of 20 days is 14 days.
SPLIT_TIME_OF_SHARE_30 = "2026-03-16T00:00:00Z"

FIRST_BAR_START = "2026-03-02T00:00:00Z"
LAST_BAR_END = "2026-03-22T00:00:00Z"


async def post_backtest(web_client: httpx.AsyncClient, strategy_version_id: int, **fields: object) -> httpx.Response:
    return await web_client.post("/api/backtests", json={**make_backtest_request(strategy_version_id), **fields})


def finish_backtest(database_url: str, backtest_id: int) -> None:
    """The status and the metrics that the backtest child saves, with no equity points."""
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            """
            UPDATE backtest SET status = 'finished', final_equity_usd = 10000, total_return_percent = 0,
                max_drawdown_percent = 0, trade_count = 0
            WHERE id = %(backtest_id)s
            """,
            {"backtest_id": backtest_id},
        )


@pytest.mark.anyio
@pytest.mark.parametrize("share", [-1, 51])
async def test_rejects_an_out_of_sample_share_outside_0_to_50(
    web_client: httpx.AsyncClient, database_url: str, share: int
) -> None:
    save_test_bars(database_url)
    saved = await save_test_strategy_version(web_client)

    response = await post_backtest(web_client, saved["strategy_version_id"], out_of_sample_share=share)

    assert response.status_code == 422
    assert (await web_client.get("/api/backtests")).json() == []


@pytest.mark.anyio
async def test_backtest_without_a_share_has_an_out_of_sample_share_of_30(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    save_test_bars(database_url)
    saved = await save_test_strategy_version(web_client)

    backtest = (await post_backtest(web_client, saved["strategy_version_id"])).json()

    assert backtest["out_of_sample_share"] == 30
    assert backtest["split_time_utc"] == SPLIT_TIME_OF_SHARE_30


@pytest.mark.anyio
async def test_split_time_is_the_start_of_the_last_share_of_the_range(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    save_test_bars(database_url)
    saved = await save_test_strategy_version(web_client)

    backtest = (
        await post_backtest(
            web_client,
            saved["strategy_version_id"],
            start_utc="2026-03-02T00:00:00Z",
            end_utc="2026-03-22T00:00:00Z",
            out_of_sample_share=25,
        )
    ).json()

    assert backtest["split_time_utc"] == "2026-03-17T00:00:00Z"


@pytest.mark.anyio
async def test_share_of_0_has_no_split(web_client: httpx.AsyncClient, database_url: str) -> None:
    save_test_bars(database_url)
    saved = await save_test_strategy_version(web_client)
    queued = (await post_backtest(web_client, saved["strategy_version_id"], out_of_sample_share=0)).json()
    finish_backtest(database_url, queued["id"])

    detail = (await web_client.get(f"/api/backtests/{queued['id']}")).json()

    assert detail["out_of_sample_share"] == 0
    assert detail["split_time_utc"] is None
    assert detail["split_metrics"] is None
    robustness = detail["robustness"]
    assert (robustness["out_of_sample_to_in_sample_sharpe_percent"], robustness["out_of_sample_use_count"]) == (
        None,
        None,
    )


@pytest.mark.anyio
async def test_no_route_changes_the_saved_split_time(web_client: httpx.AsyncClient, database_url: str) -> None:
    save_test_bars(database_url)
    saved = await save_test_strategy_version(web_client)
    queued = (await post_backtest(web_client, saved["strategy_version_id"])).json()

    patched = await web_client.patch(f"/api/backtests/{queued['id']}", json={"out_of_sample_share": 10})
    put = await web_client.put(f"/api/backtests/{queued['id']}", json={"split_time_utc": "2026-03-05T00:00:00Z"})
    finish_backtest(database_url, queued["id"])
    detail = (await web_client.get(f"/api/backtests/{queued['id']}")).json()

    assert patched.status_code == 405
    assert put.status_code == 405
    assert detail["out_of_sample_share"] == 30
    assert detail["split_time_utc"] == SPLIT_TIME_OF_SHARE_30
    listed = (await web_client.get("/api/backtests")).json()
    assert [backtest["split_time_utc"] for backtest in listed] == [SPLIT_TIME_OF_SHARE_30]


@pytest.mark.anyio
async def test_a_range_beyond_the_saved_bars_has_the_split_time_and_the_metrics_of_the_saved_bars(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    save_test_bars(database_url)
    saved = await save_test_strategy_version(web_client)
    version_id = saved["strategy_version_id"]
    bars_only = (await post_backtest(web_client, version_id, start_utc=FIRST_BAR_START, end_utc=LAST_BAR_END)).json()
    beyond_the_bars = (
        await post_backtest(web_client, version_id, start_utc="2020-01-01T00:00:00Z", end_utc="2030-01-01T00:00:00Z")
    ).json()
    async with run_backtest_runner(web_client, database_url, clock, timeout_seconds=60):
        finished = [
            await wait_for_final_status(web_client, backtest["id"]) for backtest in (bars_only, beyond_the_bars)
        ]

    assert [backtest["status"] for backtest in finished] == ["finished", "finished"]
    assert beyond_the_bars["split_time_utc"] == bars_only["split_time_utc"]
    details = [(await web_client.get(f"/api/backtests/{backtest['id']}")).json() for backtest in finished]
    assert details[1]["metrics"] == details[0]["metrics"]
    assert details[1]["split_metrics"] == details[0]["split_metrics"]


@pytest.mark.anyio
async def test_a_bar_before_the_range_does_not_put_the_split_time_before_the_first_bar_of_the_range(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    save_test_bars(database_url)
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            """
            INSERT INTO ibkr_bar (symbol, exchange, currency, bar_period, start_utc, open, high, low, close, volume)
            VALUES ('BTEST', 'ARCA', 'USD', '1-DAY', '2020-01-02T00:00:00Z', 1, 1, 1, 1, 1)
            """
        )
    saved = await save_test_strategy_version(web_client)

    backtest = (
        await post_backtest(
            web_client,
            saved["strategy_version_id"],
            start_utc="2026-02-01T00:00:00Z",
            end_utc=LAST_BAR_END,
            out_of_sample_share=50,
        )
    ).json()

    assert backtest["split_time_utc"] == "2026-03-12T00:00:00Z"


@pytest.mark.anyio
async def test_finished_backtest_has_the_metrics_of_both_parts(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    save_test_bars(database_url)
    saved = await save_test_strategy_version(web_client)
    queued = (await post_backtest(web_client, saved["strategy_version_id"])).json()
    finish_backtest(database_url, queued["id"])
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            """
            INSERT INTO backtest_equity_point (backtest_id, time_utc, equity_usd) VALUES
                (%(backtest_id)s, '2026-03-10T21:00:00Z', 10100),
                (%(backtest_id)s, '2026-03-20T21:00:00Z', 10302)
            """,
            {"backtest_id": queued["id"]},
        )

    detail = (await web_client.get(f"/api/backtests/{queued['id']}")).json()

    assert detail["split_metrics"]["in_sample"]["final_equity_usd"] == "10100"
    assert detail["split_metrics"]["in_sample"]["total_return_percent"] == "1.00"
    assert detail["split_metrics"]["out_of_sample"]["final_equity_usd"] == "10302"
    assert detail["split_metrics"]["out_of_sample"]["total_return_percent"] == "2.00"


@pytest.mark.anyio
async def test_out_of_sample_use_count_counts_finished_backtests_with_an_overlapping_out_of_sample_part(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    save_test_bars(database_url)
    saved = await save_test_strategy_version(web_client)
    version_id = saved["strategy_version_id"]
    this = (await post_backtest(web_client, version_id)).json()
    # Out-of-sample part from 2026-03-18 09:36: overlaps.
    overlapping = (await post_backtest(web_client, version_id, start_utc="2026-03-10T00:00:00Z")).json()
    # Another version of the same strategy, out-of-sample part from 2026-03-21 09:36: overlaps.
    code = TEST_STRATEGY_FILE.read_text() + "\n"
    other_version = (
        await web_client.post(f"/api/strategies/{saved['strategy_id']}/versions", json={"code": code})
    ).json()
    other_version_backtest = (
        await post_backtest(web_client, other_version["id"], start_utc="2026-03-20T00:00:00Z")
    ).json()
    # The out-of-sample part ends at the split time of this backtest: no overlap.
    before = (
        await post_backtest(web_client, version_id, start_utc="2026-03-02T00:00:00Z", end_utc=SPLIT_TIME_OF_SHARE_30)
    ).json()
    other_period = (await post_backtest(web_client, version_id)).json()
    other_instrument = (await post_backtest(web_client, version_id)).json()
    not_finished = (await post_backtest(web_client, version_id)).json()
    other_strategy = (await web_client.post("/api/strategies", json={"name": "Other"})).json()
    other_strategy_version = (
        await web_client.post(f"/api/strategies/{other_strategy['id']}/versions", json={"code": code})
    ).json()
    other_strategy_backtest = (await post_backtest(web_client, other_strategy_version["id"])).json()
    for backtest in (this, overlapping, other_version_backtest, before, other_period, other_instrument):
        finish_backtest(database_url, backtest["id"])
    finish_backtest(database_url, other_strategy_backtest["id"])
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute("UPDATE backtest SET bar_period = '1-HOUR' WHERE id = %s", [other_period["id"]])
        connection.execute("UPDATE backtest SET exchange = 'NYSE' WHERE id = %s", [other_instrument["id"]])

    robustness = (await web_client.get(f"/api/backtests/{this['id']}")).json()["robustness"]

    assert not_finished["status"] == "queued"
    assert robustness["out_of_sample_use_count"] == 3


@pytest.mark.anyio
async def test_robustness_gives_the_out_of_sample_sharpe_ratio_as_a_percent_of_the_in_sample_sharpe_ratio(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    save_test_bars(database_url)
    saved = await save_test_strategy_version(web_client)
    queued = (await post_backtest(web_client, saved["strategy_version_id"])).json()
    finish_backtest(database_url, queued["id"])
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            """
            INSERT INTO backtest_equity_point (backtest_id, time_utc, equity_usd) VALUES
                (%(backtest_id)s, '2026-03-11T21:00:00Z', 10100),
                (%(backtest_id)s, '2026-03-12T21:00:00Z', 10302),
                (%(backtest_id)s, '2026-03-13T21:00:00Z', 10200),
                (%(backtest_id)s, '2026-03-16T21:00:00Z', 10404),
                (%(backtest_id)s, '2026-03-17T21:00:00Z', 10302),
                (%(backtest_id)s, '2026-03-18T21:00:00Z', 10508)
            """,
            {"backtest_id": queued["id"]},
        )

    detail = (await web_client.get(f"/api/backtests/{queued['id']}")).json()

    assert detail["split_metrics"]["in_sample"]["sharpe_ratio"] == "6.99"
    assert detail["split_metrics"]["out_of_sample"]["sharpe_ratio"] == "9.29"
    # 9.29 / 6.99.
    robustness = detail["robustness"]
    assert (robustness["out_of_sample_to_in_sample_sharpe_percent"], robustness["out_of_sample_use_count"]) == (
        "132.90",
        1,
    )
