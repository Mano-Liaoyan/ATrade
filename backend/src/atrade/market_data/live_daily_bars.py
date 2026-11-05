"""The live daily bars of the watchlist: one shared IBKR subscription for each instrument (market_data.md 8.5.1).

Each open watchlist column follows the watchlist instruments through a listener. All listeners share one live bar
stream (`stream_live_bars`, daily bar period) for each instrument, so one instrument uses one IBKR market data line,
also with many browser tabs. The hub streams at most `max_instruments` instruments. A stream without a listener
ends after `release_delay_seconds`, so a page change does not request the bars again. A failed stream gives "no live
bar" (the page then shows the daily bars) and starts again after `retry_delay_seconds`.
"""

import asyncio
import logging
from collections.abc import Generator, Iterable
from contextlib import aclosing, contextmanager

import anyio

from atrade.foundation.bar import Bar, BarPeriod
from atrade.foundation.instrument import Instrument
from atrade.ibkr import GatewayConnection, GatewayRequestError

# IBKR allows about 100 market data lines and 50 open historical data requests at the same time. A keepUpToDate
# request uses one of each. The live bars of the charts and the forward tests need the others.
MAX_LIVE_DAILY_BAR_INSTRUMENTS = 40
RELEASE_DELAY_SECONDS = 30.0
RETRY_DELAY_SECONDS = 60.0

logger = logging.getLogger("atrade.live_daily_bars")


class LiveDailyBarListener:
    """The instruments that one socket follows, and the instruments with a change since the last `take_changes`."""

    def __init__(self, hub: LiveDailyBarHub) -> None:
        self.hub = hub
        self.instruments: set[Instrument] = set()
        # A dict keeps the order of the changes.
        self.changed: dict[Instrument, None] = {}
        self.event = anyio.Event()

    def follow(self, instruments: Iterable[Instrument]) -> None:
        """Follows these instruments only. An instrument above the limit of the hub is not followed, until a later
        call finds a free place."""
        wanted = list(dict.fromkeys(instruments))
        for instrument in self.instruments - set(wanted):
            self.instruments.discard(instrument)
            self.hub.release(instrument, self)
            self.mark_changed(instrument)
        for instrument in wanted:
            if instrument not in self.instruments and self.hub.acquire(instrument, self):
                self.instruments.add(instrument)
                self.mark_changed(instrument)

    def mark_changed(self, instrument: Instrument) -> None:
        self.changed[instrument] = None
        self.event.set()

    async def wait(self) -> None:
        """Waits until an instrument has a change that `take_changes` did not return yet."""
        await self.event.wait()

    def take_changes(self) -> dict[Instrument, Bar | None]:
        """The live bar of each changed instrument. None: no live bar (not followed, or the stream failed)."""
        changes = {
            instrument: self.hub.read_bar(instrument) if instrument in self.instruments else None
            for instrument in self.changed
        }
        self.changed = {}
        self.event = anyio.Event()
        return changes


class LiveDailyBarStream:
    """The shared stream of one instrument."""

    def __init__(self, instrument: Instrument) -> None:
        self.instrument = instrument
        self.listeners: set[LiveDailyBarListener] = set()
        self.bar: Bar | None = None
        self.task: asyncio.Task[None] | None = None
        self.release_timer: asyncio.TimerHandle | None = None


class LiveDailyBarHub:
    def __init__(
        self,
        gateway_connection: GatewayConnection,
        *,
        max_instruments: int = MAX_LIVE_DAILY_BAR_INSTRUMENTS,
        release_delay_seconds: float = RELEASE_DELAY_SECONDS,
        retry_delay_seconds: float = RETRY_DELAY_SECONDS,
    ) -> None:
        self.gateway_connection = gateway_connection
        self.max_instruments = max_instruments
        self.release_delay_seconds = release_delay_seconds
        self.retry_delay_seconds = retry_delay_seconds
        self.streams: dict[Instrument, LiveDailyBarStream] = {}

    @contextmanager
    def listen(self) -> Generator[LiveDailyBarListener]:
        """A listener for one socket. At the end it follows no instrument."""
        listener = LiveDailyBarListener(self)
        try:
            yield listener
        finally:
            listener.follow([])

    def acquire(self, instrument: Instrument, listener: LiveDailyBarListener) -> bool:
        """Adds the listener to the stream of the instrument. False when the hub has no free place."""
        stream = self.streams.get(instrument)
        if stream is None:
            if len(self.streams) >= self.max_instruments and not self.stop_one_unused_stream():
                return False
            stream = LiveDailyBarStream(instrument)
            self.streams[instrument] = stream
            stream.task = asyncio.create_task(self.keep_streaming(stream))
        if stream.release_timer is not None:
            stream.release_timer.cancel()
            stream.release_timer = None
        stream.listeners.add(listener)
        return True

    def release(self, instrument: Instrument, listener: LiveDailyBarListener) -> None:
        stream = self.streams.get(instrument)
        if stream is None:
            return
        stream.listeners.discard(listener)
        if not stream.listeners and stream.release_timer is None:
            loop = asyncio.get_running_loop()
            stream.release_timer = loop.call_later(self.release_delay_seconds, self.stop_stream, instrument)

    def read_bar(self, instrument: Instrument) -> Bar | None:
        stream = self.streams.get(instrument)
        return None if stream is None else stream.bar

    def stop(self) -> None:
        """Ends all streams. The lifespan calls it when the Web process stops."""
        for instrument in list(self.streams):
            self.stop_stream(instrument)

    def stop_stream(self, instrument: Instrument) -> None:
        """Cancels the task. Its `aclosing` closes the live bar generator, which ends the IBKR subscription."""
        stream = self.streams.pop(instrument, None)
        if stream is None:
            return
        if stream.release_timer is not None:
            stream.release_timer.cancel()
        if stream.task is not None:
            stream.task.cancel()

    def stop_one_unused_stream(self) -> bool:
        """A stream in its release delay gives its place to a new instrument."""
        for instrument, stream in self.streams.items():
            if not stream.listeners:
                self.stop_stream(instrument)
                return True
        return False

    async def keep_streaming(self, stream: LiveDailyBarStream) -> None:
        while True:
            try:
                async with aclosing(
                    self.gateway_connection.stream_live_bars(stream.instrument, BarPeriod.ONE_DAY)
                ) as live_bars:
                    async for bar in live_bars:
                        self.publish(stream, bar)
            except GatewayRequestError as error:
                logger.info("The live daily bars of %s stopped: %s", stream.instrument, error)
            self.publish(stream, None)
            await asyncio.sleep(self.retry_delay_seconds)

    def publish(self, stream: LiveDailyBarStream, bar: Bar | None) -> None:
        stream.bar = bar
        for listener in stream.listeners:
            listener.mark_changed(stream.instrument)
