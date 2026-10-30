"""A backtest that the AI assistant starts records its conversation (docs/architecture/backtest.md 10.2.1).

`start_backtest` is the function that port 8001 calls (#181). No real model provider runs: the conversation comes
from the routes with the fake assistant service.
"""

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from atrade.backtest import BacktestRefusal, BacktestRequest, start_backtest
from atrade.foundation.bar import BarPeriod, TimeRange
from atrade.foundation.instrument import Instrument
from atrade.market_data import ExchangeRateReader
from tests.assistant.assistant_app import create_conversation, create_strategy, open_assistant_client
from tests.backtest.real_runner import TEST_STRATEGY_FILE, save_test_bars
from tests.fakes.assistant import FakeAssistantService
from tests.fakes.clock import FixedClock
from tests.fakes.ibkr import FakeGatewayConnection


def make_request(strategy_version_id: int) -> BacktestRequest:
    return BacktestRequest(
        strategy_version_id=strategy_version_id,
        instrument=Instrument(symbol="BTEST", exchange="ARCA", currency="USD"),
        bar_period=BarPeriod.ONE_DAY,
        time_range=TimeRange(start_utc=datetime(2026, 3, 1, tzinfo=UTC), end_utc=datetime(2026, 4, 1, tzinfo=UTC)),
        paper_capital_usd=Decimal(10000),
    )


@pytest.mark.anyio
async def test_a_backtest_of_the_ai_assistant_records_the_conversation(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    save_test_bars(database_url)
    async with open_assistant_client(
        database_url=database_url,
        clock=clock,
        frontend_build_dir=frontend_build_dir,
        assistant_service=FakeAssistantService(),
    ) as client:
        strategy_id = await create_strategy(client, "Bar count")
        conversation_id = await create_conversation(client, strategy_id)
        version = (
            await client.post(f"/api/strategies/{strategy_id}/versions", json={"code": TEST_STRATEGY_FILE.read_text()})
        ).json()
        reader = ExchangeRateReader(
            database_url=database_url, clock=clock, gateway_connection=FakeGatewayConnection(managed_accounts=[])
        )

        started = await start_backtest(
            database_url=database_url,
            exchange_rate_reader=reader,
            request=make_request(version["id"]),
            created_at_utc=clock.read_now_utc(),
            conversation_id=conversation_id,
        )

        assert not isinstance(started, BacktestRefusal)
        backtest = (await client.get(f"/api/backtests/{started}")).json()
        assert backtest["conversation_id"] == conversation_id
        user_backtest = await client.post(
            "/api/backtests",
            json={
                "strategy_version_id": version["id"],
                "symbol": "BTEST",
                "exchange": "ARCA",
                "currency": "USD",
                "bar_period": "1-DAY",
                "start_utc": "2026-03-01T00:00:00Z",
                "end_utc": "2026-04-01T00:00:00Z",
                "paper_capital_usd": "10000",
            },
        )
        assert user_backtest.json()["conversation_id"] is None


@pytest.mark.anyio
async def test_a_refused_start_names_the_reason(database_url: str, clock: FixedClock) -> None:
    reader = ExchangeRateReader(
        database_url=database_url, clock=clock, gateway_connection=FakeGatewayConnection(managed_accounts=[])
    )

    started = await start_backtest(
        database_url=database_url,
        exchange_rate_reader=reader,
        request=make_request(999),
        created_at_utc=clock.read_now_utc(),
        conversation_id=None,
    )

    assert started == BacktestRefusal("Strategy version 999 does not exist.")
