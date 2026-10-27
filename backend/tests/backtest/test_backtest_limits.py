"""The backtest limits (timeout and concurrency) through the HTTP routes. PostgreSQL stores them."""

import httpx
import pytest


@pytest.mark.anyio
async def test_limits_are_120_minutes_and_1_backtest_by_default(web_client: httpx.AsyncClient) -> None:
    response = await web_client.get("/api/backtest-limits")

    assert response.status_code == 200
    assert response.json() == {"timeout_seconds": 7200, "concurrency": 1}


@pytest.mark.anyio
async def test_changed_limits_are_kept(web_client: httpx.AsyncClient) -> None:
    response = await web_client.put("/api/backtest-limits", json={"timeout_seconds": 600, "concurrency": 3})

    assert response.status_code == 200
    assert response.json() == {"timeout_seconds": 600, "concurrency": 3}
    assert (await web_client.get("/api/backtest-limits")).json() == {"timeout_seconds": 600, "concurrency": 3}


@pytest.mark.anyio
@pytest.mark.parametrize(
    "limits",
    [
        {"timeout_seconds": 0, "concurrency": 1},
        {"timeout_seconds": 600, "concurrency": 0},
        {"timeout_seconds": 600, "concurrency": 17},
        {"timeout_seconds": 604801, "concurrency": 1},
        {"timeout_seconds": 600},
    ],
)
async def test_rejects_limits_out_of_range(web_client: httpx.AsyncClient, limits: dict[str, int]) -> None:
    response = await web_client.put("/api/backtest-limits", json=limits)

    assert response.status_code == 422
    assert (await web_client.get("/api/backtest-limits")).json() == {"timeout_seconds": 7200, "concurrency": 1}
