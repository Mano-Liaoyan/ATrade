"""The Instruments of a multi-instrument backtest and the first and last day with US universe data
(docs/architecture/backtest.md sections 10.10.6 and 10.10.7)."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

import httpx
import pytest

from atrade.backtest.backtest_metrics import BacktestTrade
from atrade.backtest.universe_instruments import summarize_instruments
from tests.backtest.test_backtest_routes import save_test_strategy_version
from tests.backtest.universe_data import (
    FIRST_QUARTER_START_UTC,
    SECOND_QUARTER_START_UTC,
    make_universe_request,
    save_universe_test_data,
)


def make_trade(day: int, side: Literal["BUY", "SELL"], price: str, symbol: str, exchange: str) -> BacktestTrade:
    return BacktestTrade(
        time_utc=datetime(2026, 3, day, tzinfo=UTC),
        side=side,
        quantity_shares=Decimal(10),
        price_usd=Decimal(price),
        commission_usd=Decimal(0),
        symbol=symbol,
        exchange=exchange,
    )


def test_each_member_has_its_trade_count_net_profit_and_quarter_count() -> None:
    trades = [
        make_trade(2, "BUY", "10", "AAA", "NASDAQ"),
        make_trade(3, "SELL", "12", "AAA", "NASDAQ"),
        make_trade(4, "BUY", "20", "BBB", "NYSE"),
    ]
    quarter_counts = {("AAA", "NASDAQ"): 1, ("BBB", "NYSE"): 2, ("CCC", "ARCA"): 1}

    instruments = summarize_instruments(trades, quarter_counts)

    assert [(item.symbol, item.trade_count, item.net_profit_usd, item.quarter_count) for item in instruments] == [
        ("AAA", 2, Decimal(20), 1),
        ("BBB", 1, Decimal(0), 2),
        ("CCC", 0, Decimal(0), 1),
    ]


@pytest.mark.anyio
async def test_a_rule_backtest_lists_each_member_with_its_quarter_count(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    save_universe_test_data(database_url)
    saved = await save_test_strategy_version(web_client)
    started = await web_client.post(
        "/api/backtests", json=make_universe_request(saved["strategy_version_id"], universe_kind="rule", top_n=2)
    )

    backtest = (await web_client.get(f"/api/backtests/{started.json()['id']}")).json()

    assert [(item["symbol"], item["quarter_count"]) for item in backtest["instruments"]] == [
        ("AAA", 1),
        ("BBB", 2),
        ("CCC", 1),
    ]


@pytest.mark.anyio
async def test_the_universe_range_is_the_first_and_last_quarter_start(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    save_universe_test_data(database_url)

    response = await web_client.get("/api/us-universe/range")

    assert response.json() == {
        "first_day_utc": FIRST_QUARTER_START_UTC.isoformat().replace("+00:00", "Z"),
        "last_day_utc": SECOND_QUARTER_START_UTC.isoformat().replace("+00:00", "Z"),
    }


@pytest.mark.anyio
async def test_the_universe_range_is_null_without_universe_data(web_client: httpx.AsyncClient) -> None:
    response = await web_client.get("/api/us-universe/range")

    assert response.json() == {"first_day_utc": None, "last_day_utc": None}
