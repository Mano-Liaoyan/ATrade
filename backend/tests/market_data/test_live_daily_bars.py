"""LiveDailyBarHub: the shared live daily bar streams of the watchlist, with the IBKR fake (market_data.md 8.5.1).

The fake updates its current daily bar (2026-01-02) a few times each second (tests/fakes/ibkr.py).
"""

from collections.abc import Callable
from datetime import UTC, datetime

import anyio
import pytest

from atrade.foundation.bar import Bar, BarPeriod
from atrade.foundation.instrument import Instrument
from atrade.market_data import LiveDailyBarHub, LiveDailyBarListener
from tests.fakes.ibkr import FakeGatewayConnection, LiveBarSubscription

TENCENT = Instrument(symbol="700", exchange="SEHK", currency="HKD")
APPLE = Instrument(symbol="AAPL", exchange="NASDAQ", currency="USD")
ALIBABA = Instrument(symbol="9988", exchange="SEHK", currency="HKD")
WAIT_SECONDS = 5
DAILY_BAR_START_UTC = datetime(2026, 1, 2, tzinfo=UTC)


def make_connected_gateway() -> FakeGatewayConnection:
    gateway_connection = FakeGatewayConnection(managed_accounts=["DU1234567"])
    gateway_connection.connected = True
    return gateway_connection


async def wait_until(condition: Callable[[], bool]) -> None:
    with anyio.fail_after(WAIT_SECONDS):
        while not condition():
            await anyio.sleep(0.01)


async def take_changes_with_bars(listener: LiveDailyBarListener, count: int) -> dict[Instrument, Bar | None]:
    """Waits until `count` instruments have a live bar and returns the last change of each instrument."""
    changes: dict[Instrument, Bar | None] = {}
    with anyio.fail_after(WAIT_SECONDS):
        while sum(bar is not None for bar in changes.values()) < count:
            await listener.wait()
            changes.update(listener.take_changes())
    return changes


@pytest.mark.anyio
async def test_listeners_of_one_instrument_share_one_ibkr_subscription() -> None:
    gateway_connection = make_connected_gateway()
    hub = LiveDailyBarHub(gateway_connection)

    with hub.listen() as first_tab, hub.listen() as second_tab:
        first_tab.follow([TENCENT, APPLE])
        second_tab.follow([TENCENT])
        first_changes = await take_changes_with_bars(first_tab, 2)
        second_changes = await take_changes_with_bars(second_tab, 1)
        hub.stop()

    assert gateway_connection.live_bar_subscriptions == [
        LiveBarSubscription(TENCENT, BarPeriod.ONE_DAY),
        LiveBarSubscription(APPLE, BarPeriod.ONE_DAY),
    ]
    tencent_bar = first_changes[TENCENT]
    assert tencent_bar is not None
    assert tencent_bar.start_utc == DAILY_BAR_START_UTC
    assert set(second_changes) == {TENCENT}


@pytest.mark.anyio
async def test_ends_the_subscription_after_the_release_delay_when_no_listener_is_left() -> None:
    gateway_connection = make_connected_gateway()
    hub = LiveDailyBarHub(gateway_connection, release_delay_seconds=0.3)

    with hub.listen() as first_tab:
        first_tab.follow([TENCENT])
        await take_changes_with_bars(first_tab, 1)
    # A page change opens the next socket within the delay: the stream stays.
    with hub.listen() as second_tab:
        second_tab.follow([TENCENT])
        await take_changes_with_bars(second_tab, 1)
    await wait_until(lambda: gateway_connection.active_live_bar_stream_count == 0)

    assert gateway_connection.live_bar_subscriptions == [LiveBarSubscription(TENCENT, BarPeriod.ONE_DAY)]


@pytest.mark.anyio
async def test_ends_the_subscription_of_an_instrument_that_leaves_the_list() -> None:
    gateway_connection = make_connected_gateway()
    hub = LiveDailyBarHub(gateway_connection, release_delay_seconds=0)

    with hub.listen() as tab:
        tab.follow([TENCENT, APPLE])
        await take_changes_with_bars(tab, 2)
        tab.follow([APPLE])
        await wait_until(lambda: gateway_connection.active_live_bar_stream_count == 1)
        changes = tab.take_changes()
        hub.stop()

    # The listener gets "no live bar" for the instrument that it does not follow now.
    assert TENCENT in changes
    assert changes[TENCENT] is None


@pytest.mark.anyio
async def test_streams_at_most_the_limit_and_takes_the_next_instrument_when_one_leaves() -> None:
    gateway_connection = make_connected_gateway()
    hub = LiveDailyBarHub(gateway_connection, max_instruments=2, release_delay_seconds=0)

    with hub.listen() as tab:
        tab.follow([TENCENT, APPLE, ALIBABA])
        first_changes = await take_changes_with_bars(tab, 2)
        assert set(first_changes) == {TENCENT, APPLE}
        assert gateway_connection.active_live_bar_stream_count == 2

        tab.follow([APPLE, ALIBABA])
        second_changes = await take_changes_with_bars(tab, 2)
        hub.stop()

    assert ALIBABA in second_changes
    assert [subscription.instrument for subscription in gateway_connection.live_bar_subscriptions] == [
        TENCENT,
        APPLE,
        ALIBABA,
    ]


@pytest.mark.anyio
async def test_a_failed_subscription_gives_no_live_bar_and_starts_again_after_the_retry_delay() -> None:
    gateway_connection = make_connected_gateway()
    gateway_connection.live_bars_error_message = "No market data permissions for SEHK STK"
    hub = LiveDailyBarHub(gateway_connection, retry_delay_seconds=0.2)

    with hub.listen() as tab:
        tab.follow([TENCENT])
        with anyio.fail_after(WAIT_SECONDS):
            await tab.wait()
        assert tab.take_changes() == {TENCENT: None}
        await wait_until(lambda: len(gateway_connection.live_bar_subscriptions) >= 2)
        gateway_connection.live_bars_error_message = None
        changes = await take_changes_with_bars(tab, 1)
        hub.stop()

    assert changes[TENCENT] is not None


@pytest.mark.anyio
async def test_gives_no_live_bar_without_ib_gateway() -> None:
    gateway_connection = FakeGatewayConnection(managed_accounts=["DU1234567"])
    hub = LiveDailyBarHub(gateway_connection)

    with hub.listen() as tab:
        tab.follow([TENCENT])
        with anyio.fail_after(WAIT_SECONDS):
            await tab.wait()
        changes = tab.take_changes()
        hub.stop()

    assert changes == {TENCENT: None}
    assert gateway_connection.live_bar_subscriptions == []
