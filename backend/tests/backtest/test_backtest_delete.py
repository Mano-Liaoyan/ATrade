"""DELETE /api/backtests/{backtest_id}: a true delete of a backtest and the rules that refuse it (section 10.5)."""

import httpx
import psycopg
import pytest

from tests.backtest.real_runner import save_test_bars
from tests.backtest.test_backtest_routes import make_backtest_request, save_test_strategy_version


async def start_backtest(web_client: httpx.AsyncClient, database_url: str) -> dict[str, int]:
    save_test_bars(database_url)
    saved = await save_test_strategy_version(web_client)
    backtest = (
        await web_client.post("/api/backtests", json=make_backtest_request(saved["strategy_version_id"]))
    ).json()
    return {"backtest_id": backtest["id"], "strategy_version_id": saved["strategy_version_id"]}


def set_status(database_url: str, backtest_id: int, status: str) -> None:
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            "UPDATE backtest SET status = %(status)s, error_message = 'Boom' WHERE id = %(backtest_id)s",
            {"status": status, "backtest_id": backtest_id},
        )


@pytest.mark.anyio
@pytest.mark.parametrize("status", ["finished", "failed", "timed_out", "cancelled"])
async def test_deletes_a_backtest_with_a_final_status(
    web_client: httpx.AsyncClient, database_url: str, status: str
) -> None:
    started = await start_backtest(web_client, database_url)
    set_status(database_url, started["backtest_id"], status)

    response = await web_client.delete(f"/api/backtests/{started['backtest_id']}")

    assert response.status_code == 204
    assert (await web_client.get(f"/api/backtests/{started['backtest_id']}")).status_code == 404
    assert (await web_client.get("/api/backtests")).json() == []


@pytest.mark.anyio
async def test_delete_of_a_missing_backtest_is_not_found(web_client: httpx.AsyncClient) -> None:
    response = await web_client.delete("/api/backtests/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Backtest not found."}


@pytest.mark.anyio
@pytest.mark.parametrize("status", ["queued", "running"])
async def test_refuses_to_delete_a_backtest_that_has_not_ended(
    web_client: httpx.AsyncClient, database_url: str, status: str
) -> None:
    started = await start_backtest(web_client, database_url)
    set_status(database_url, started["backtest_id"], status)

    response = await web_client.delete(f"/api/backtests/{started['backtest_id']}")

    assert response.status_code == 409
    assert response.json() == {"detail": f"Backtest #{started['backtest_id']} is {status}. Wait for its end."}
    assert (await web_client.get(f"/api/backtests/{started['backtest_id']}")).status_code == 200


@pytest.mark.anyio
async def test_refuses_to_delete_a_sweep_run(web_client: httpx.AsyncClient, database_url: str) -> None:
    started = await start_backtest(web_client, database_url)
    set_status(database_url, started["backtest_id"], "finished")
    with psycopg.connect(database_url, autocommit=True) as connection:
        sweep = connection.execute(
            """
            INSERT INTO parameter_sweep (strategy_version_id, grid, created_at_utc)
            VALUES (%(version_id)s, '{}', now()) RETURNING id
            """,
            {"version_id": started["strategy_version_id"]},
        ).fetchone()
        assert sweep is not None
        connection.execute(
            "UPDATE backtest SET sweep_id = %(sweep_id)s WHERE id = %(backtest_id)s",
            {"sweep_id": sweep[0], "backtest_id": started["backtest_id"]},
        )

    response = await web_client.delete(f"/api/backtests/{started['backtest_id']}")

    assert response.status_code == 409
    assert response.json() == {
        "detail": f"Backtest #{started['backtest_id']} is a run of sweep #{sweep[0]}. Delete the sweep."
    }


@pytest.mark.anyio
async def test_refuses_to_delete_the_same_period_backtest_of_a_forward_test(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    started = await start_backtest(web_client, database_url)
    set_status(database_url, started["backtest_id"], "finished")
    with psycopg.connect(database_url, autocommit=True) as connection:
        forward_test = connection.execute(
            """
            INSERT INTO forward_test (strategy_version_id, symbol, exchange, currency, bar_period, desired_state,
                status, start_balance_usd, created_at_utc, stopped_at_utc)
            VALUES (%(version_id)s, 'BTEST', 'ARCA', 'USD', '1-DAY', 'stopped', 'stopped', 10000, now(), now())
            RETURNING id
            """,
            {"version_id": started["strategy_version_id"]},
        ).fetchone()
        assert forward_test is not None
        connection.execute(
            """
            INSERT INTO forward_test_same_period_backtest (forward_test_id, backtest_id)
            VALUES (%(forward_test_id)s, %(backtest_id)s)
            """,
            {"forward_test_id": forward_test[0], "backtest_id": started["backtest_id"]},
        )

    response = await web_client.delete(f"/api/backtests/{started['backtest_id']}")

    assert response.status_code == 409
    assert response.json() == {
        "detail": f"Backtest #{started['backtest_id']} is the same-period backtest of a forward test."
    }
