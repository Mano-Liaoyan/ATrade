"""The ATrade data client in a real LiveNode: `request_bars` and `on_bar` get the bars of the bar store
(docs/architecture/forward_test.md section 12.19)."""

from datetime import UTC, datetime, timedelta

import pytest

from tests.forward_test.atrade_clients_node import (
    make_day_bar,
    make_strategy,
    make_world,
    run_node,
    save_day_bars,
    send_today_bar,
    wait_until,
)

SAVED_CLOSES = ["10.5", "11.25", "12"]
FIRST_DAY_UTC = datetime(2026, 3, 2, tzinfo=UTC)


@pytest.mark.anyio
async def test_request_bars_and_on_bar_get_the_bars_of_the_bar_store(database_url: str) -> None:
    world = make_world(database_url)
    await save_day_bars(
        database_url,
        [make_day_bar(FIRST_DAY_UTC + timedelta(days=index), close) for index, close in enumerate(SAVED_CLOSES)],
    )

    strategy = make_strategy(claims_external_orders=True)
    async with run_node(world, strategy, 1) as data_factory:
        await wait_until(lambda: bool(strategy.historical_bars))
        # No bar before the bar fetcher saves a new one.
        assert data_factory.client is not None
        await data_factory.client.send_new_bars()
        bars_before_save = len(strategy.bars)
        await send_today_bar(world, data_factory, "13.5")
        await wait_until(lambda: bool(strategy.bars))

    assert [str(bar.close) for bar in strategy.historical_bars] == ["10.5000", "11.2500", "12.0000"]
    # ts_event is the bar end.
    assert strategy.historical_bars[0].ts_event == int((FIRST_DAY_UTC + timedelta(days=1)).timestamp()) * 10**9
    assert bars_before_save == 0
    assert [str(bar.close) for bar in strategy.bars] == ["13.5000"]
