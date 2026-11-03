"""The net profit of the round trip that a trade ends, for the trade marks of the bar chart
(docs/architecture/indicator.md section 23.9.9)."""

import httpx
import psycopg
import pytest

from tests.backtest.real_runner import save_test_bars
from tests.backtest.test_backtest_routes import make_backtest_request, save_test_strategy_version
from tests.forward_test.test_universe_forward_test_detail import save_ledger_fill, start_watchlist_forward_test


@pytest.mark.anyio
async def test_each_backtest_trade_has_the_net_profit_of_the_round_trip_that_it_ends(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    save_test_bars(database_url)
    saved = await save_test_strategy_version(web_client)
    backtest = (
        await web_client.post("/api/backtests", json=make_backtest_request(saved["strategy_version_id"]))
    ).json()
    with psycopg.connect(database_url, autocommit=True) as connection, connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO backtest_trade (backtest_id, time_utc, side, quantity_shares, price_usd, commission_usd)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            [
                (backtest["id"], "2026-03-02T00:00:00Z", "BUY", 10, "100.00", "1.00"),
                (backtest["id"], "2026-03-03T00:00:00Z", "BUY", 10, "102.00", "1.00"),
                (backtest["id"], "2026-03-04T00:00:00Z", "SELL", 20, "105.00", "1.25"),
                (backtest["id"], "2026-03-05T00:00:00Z", "BUY", 5, "104.00", "1.00"),
            ],
        )

    detail = (await web_client.get(f"/api/backtests/{backtest['id']}")).json()

    # 20 * 105 - 10 * 100 - 10 * 102 - 3.25 commissions = 76.75. The last buy opens a round trip that has no end.
    assert [trade["round_trip_net_profit_usd"] for trade in detail["trades"]] == [None, None, "76.75", None]


@pytest.mark.anyio
async def test_a_forward_test_fill_has_the_round_trip_net_profit_and_a_split_adjustment_has_none(
    web_client: httpx.AsyncClient, database_url: str
) -> None:
    forward_test = await start_watchlist_forward_test(web_client, database_url, ["AAPL"])
    await save_ledger_fill(database_url, forward_test["id"], "BUY", "100", 1)
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            """
            INSERT INTO owner_ledger_entry (owner_kind, forward_test_id, entry_kind, time_utc, account, symbol,
                exchange, currency, quantity_change, cash_change, stock_split_id)
            VALUES ('forward_test', %s, 'split_adjustment', '2026-01-07T00:00:00Z', 'DU1234567', 'AAPL', 'NASDAQ',
                'USD', 0, 7.5, 1)
            """,
            (forward_test["id"],),
        )
    await save_ledger_fill(database_url, forward_test["id"], "SELL", "110", 2)

    fills = (await web_client.get(f"/api/forward-tests/{forward_test['id']}")).json()["fills"]

    assert [(fill["kind"], fill["round_trip_net_profit_usd"]) for fill in fills] == [
        ("fill", None),
        ("split_adjustment", None),
        ("fill", "100"),
    ]
