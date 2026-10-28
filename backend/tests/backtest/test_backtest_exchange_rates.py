"""Backtests of instruments that are not in USD: POST /api/backtests saves the daily exchange rates from the IBKR fake,
and a real child process converts the results to USD (docs/architecture/backtest.md section 10.8).
"""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import httpx
import psycopg
import pytest

from atrade.app.web import create_web_app
from atrade.foundation.bar import TimeRange
from atrade.foundation.settings import Settings
from tests.backtest.real_runner import TEST_STRATEGY_FILE, run_backtest_runner, save_test_bars, wait_for_final_status
from tests.fakes.clock import FixedClock
from tests.fakes.ibkr import DailyExchangeRateRequest, FakeGatewayConnection

# The test bars end on 2026-03-21. At this time all daily rates of the backtest range are complete.
NOW_UTC = datetime(2026, 4, 10, tzinfo=UTC)
HKD_USD_RATE = Decimal("0.128")


def save_two_hkd_rates(database_url: str) -> None:
    """Saves the HKD rates of 2026-02-22 to 2026-03-31: 0.128 USD to 2026-03-09, then 0.126 USD."""
    first_day_utc = datetime(2026, 2, 22, tzinfo=UTC)
    rate_change_utc = datetime(2026, 3, 10, tzinfo=UTC)
    end_utc = datetime(2026, 4, 1, tzinfo=UTC)
    days_utc = [first_day_utc + timedelta(days=day) for day in range((end_utc - first_day_utc).days)]
    with psycopg.connect(database_url, autocommit=True) as connection, connection.cursor() as cursor:
        cursor.executemany(
            "INSERT INTO exchange_rate (currency, day_start_utc, usd_per_unit) VALUES ('HKD', %s, %s)",
            [(day_utc, Decimal("0.128") if day_utc < rate_change_utc else Decimal("0.126")) for day_utc in days_utc],
        )
        cursor.execute(
            "INSERT INTO exchange_rate_saved_range (currency, start_utc, end_utc) VALUES ('HKD', %s, %s)",
            (first_day_utc, end_utc),
        )


@pytest.fixture
def gateway_connection() -> FakeGatewayConnection:
    connection = FakeGatewayConnection(managed_accounts=["DU1234567"])
    connection.connected = True
    connection.daily_exchange_rates = {("HKD", "USD"): HKD_USD_RATE}
    return connection


@pytest.fixture
async def client(
    database_url: str, frontend_build_dir: Path, gateway_connection: FakeGatewayConnection
) -> AsyncIterator[httpx.AsyncClient]:
    settings = Settings(database_url=database_url, frontend_build_dir=frontend_build_dir)
    app = create_web_app(settings=settings, clock=FixedClock(NOW_UTC), gateway_connection=gateway_connection)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http_client:
        yield http_client


async def save_strategy_version(client: httpx.AsyncClient) -> int:
    strategy = (await client.post("/api/strategies", json={"name": "Bar count"})).json()
    code = TEST_STRATEGY_FILE.read_text()
    version = (await client.post(f"/api/strategies/{strategy['id']}/versions", json={"code": code})).json()
    return version["id"]


def make_hkd_request(strategy_version_id: int) -> dict[str, object]:
    return {
        "strategy_version_id": strategy_version_id,
        "symbol": "BTEST",
        "exchange": "SEHK",
        "currency": "HKD",
        "bar_period": "1-DAY",
        "start_utc": "2026-03-01T00:00:00Z",
        "end_utc": "2026-04-01T00:00:00Z",
        "paper_capital_usd": "10000",
    }


@pytest.mark.anyio
async def test_a_backtest_in_hkd_saves_the_daily_exchange_rates_from_ibkr(
    client: httpx.AsyncClient, database_url: str, gateway_connection: FakeGatewayConnection
) -> None:
    save_test_bars(database_url, exchange="SEHK", currency="HKD")
    strategy_version_id = await save_strategy_version(client)

    response = await client.post("/api/backtests", json=make_hkd_request(strategy_version_id))

    assert response.status_code == 201, response.json()
    assert response.json()["status"] == "queued"
    # The range starts 7 days before the backtest start, so the start has the rate of a complete day before it.
    assert gateway_connection.daily_exchange_rate_requests == [
        DailyExchangeRateRequest(
            currency="HKD",
            quote_currency="USD",
            time_range=TimeRange(datetime(2026, 2, 22, tzinfo=UTC), datetime(2026, 4, 1, tzinfo=UTC)),
        )
    ]


@pytest.mark.anyio
async def test_a_second_backtest_in_hkd_uses_the_saved_exchange_rates(
    client: httpx.AsyncClient, database_url: str, gateway_connection: FakeGatewayConnection
) -> None:
    save_test_bars(database_url, exchange="SEHK", currency="HKD")
    strategy_version_id = await save_strategy_version(client)
    await client.post("/api/backtests", json=make_hkd_request(strategy_version_id))
    gateway_connection.connected = False

    response = await client.post("/api/backtests", json=make_hkd_request(strategy_version_id))

    assert response.status_code == 201, response.json()
    assert len(gateway_connection.daily_exchange_rate_requests) == 1


@pytest.mark.anyio
async def test_a_backtest_in_hkd_is_refused_without_saved_rates_and_without_ib_gateway(
    client: httpx.AsyncClient, database_url: str, gateway_connection: FakeGatewayConnection
) -> None:
    save_test_bars(database_url, exchange="SEHK", currency="HKD")
    strategy_version_id = await save_strategy_version(client)
    gateway_connection.connected = False

    response = await client.post("/api/backtests", json=make_hkd_request(strategy_version_id))

    assert response.status_code == 422
    assert response.json() == {
        "detail": "A backtest of a HKD instrument needs the daily HKD to USD exchange rates from IBKR"
        " from 2026-02-22 00:00 UTC to 2026-04-01 00:00 UTC. ATrade is not connected to IB Gateway."
        " Connect IB Gateway and start the backtest again."
    }
    assert (await client.get("/api/backtests")).json() == []


@pytest.mark.anyio
async def test_a_backtest_is_refused_when_ibkr_has_no_exchange_rate(
    client: httpx.AsyncClient, database_url: str, gateway_connection: FakeGatewayConnection
) -> None:
    save_test_bars(database_url, exchange="SEHK", currency="HKD")
    strategy_version_id = await save_strategy_version(client)
    gateway_connection.daily_exchange_rates = {}

    response = await client.post("/api/backtests", json=make_hkd_request(strategy_version_id))

    assert response.status_code == 422
    assert response.json()["detail"].endswith("IBKR did not return them: IBKR has no HKD to USD exchange rate.")


@pytest.mark.anyio
async def test_a_backtest_in_hkd_shows_the_results_in_usd(
    client: httpx.AsyncClient, database_url: str, gateway_connection: FakeGatewayConnection
) -> None:
    save_test_bars(database_url, exchange="SEHK", currency="HKD")
    save_two_hkd_rates(database_url)
    strategy_version_id = await save_strategy_version(client)
    backtest_id = (await client.post("/api/backtests", json=make_hkd_request(strategy_version_id))).json()["id"]

    async with run_backtest_runner(client, database_url, FixedClock(NOW_UTC), timeout_seconds=60):
        backtest = await wait_for_final_status(client, backtest_id)

    assert backtest["status"] == "finished", backtest["error_message"]
    assert gateway_connection.daily_exchange_rate_requests == []
    # The engine starts with 10000 / 0.128 = 78125 HKD. Each value uses the rate of the last day that ended before it:
    # 0.128 to 2026-03-10 00:00, then 0.126. The fills are at 104, 106, and 96 HKD.
    assert [(trade["side"], trade["price_usd"]) for trade in backtest["trades"]] == [
        ("BUY", "13.3120"),
        ("SELL", "13.5680"),
        ("BUY", "12.0960"),
    ]
    # The HKD equity is 78125 plus 0, 20, 40, ... 160 HKD of trading profit (the USD backtest has the same profit).
    assert [point["equity_usd"] for point in backtest["equity_curve"]] == [
        "10000.00", "10000.00", "10000.00", "10002.56", "10005.12", "10007.68", "10005.12", "10002.56",
        "9846.27", "9846.27", "9846.27", "9846.27", "9846.27", "9848.79", "9851.31", "9853.83",
        "9856.35", "9858.87", "9861.39", "9863.91",
    ]  # fmt: skip
    # The HKD fall from 0.128 to 0.126 USD is a loss in USD: 161.41 / 10007.68 = 1.61 %.
    assert backtest["metrics"] == {
        "final_equity_usd": "9863.91",
        "total_return_percent": "-1.36",
        "max_drawdown_percent": "1.61",
        "trade_count": 3,
    }
