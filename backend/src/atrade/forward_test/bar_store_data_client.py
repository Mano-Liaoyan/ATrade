"""`BarStoreDataClient`: a NautilusTrader data client that gives the strategy the bars of the bar store
(docs/architecture/forward_test.md section 12.19). It never asks IBKR.

New bars: the caller saves them in the bar store and calls `send_new_bars` (section 12.24, #217 decides the
production caller).
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import override

from nautilus_trader.common import Clock
from nautilus_trader.config import DataClientConfig
from nautilus_trader.live import BarsResponse, ClientCache, RequestBars, SubscribeBars, UnsubscribeBars
from nautilus_trader.live.clients import DataClient, DataClientFactory
from nautilus_trader.model import BarType

from atrade.forward_test.atrade_instruments import convert_bar, create_equity, read_bar_period
from atrade.foundation.bar import Bar, TimeRange, floor_to_bar_start
from atrade.foundation.instrument import Instrument
from atrade.market_data import BarRequest, read_saved_bars

BAR_STORE_DATA_CLIENT_NAME = "ATRADE_BAR_STORE"
# A request without a start reads from this time.
FIRST_BAR_UTC = datetime(1970, 1, 1, tzinfo=UTC)
NANOSECONDS_PER_SECOND = 1_000_000_000


@dataclass(frozen=True)
class BarStoreInput:
    database_url: str
    instruments: tuple[Instrument, ...]


def read_utc(clock: Clock) -> datetime:
    return datetime.fromtimestamp(clock.timestamp_ns() / NANOSECONDS_PER_SECOND, UTC)


class BarStoreDataClient(DataClient):
    def __init__(
        self, *, name: str, config: DataClientConfig, cache: ClientCache, clock: Clock, bar_store_input: BarStoreInput
    ) -> None:
        super().__init__(name=name, config=config, cache=cache, clock=clock, venue=None)
        self.bar_store_input = bar_store_input
        self.instruments = {str(create_equity(instrument).id): instrument for instrument in bar_store_input.instruments}
        # Bar type -> the start of the next bar to send.
        self.next_bar_starts: dict[BarType, datetime] = {}

    @override
    async def _connect(self) -> None:
        for instrument in self.bar_store_input.instruments:
            self._handle_instrument(create_equity(instrument))

    @override
    async def _disconnect(self) -> None:
        self.next_bar_starts.clear()

    async def read_bars(self, bar_type: BarType, time_range: TimeRange) -> list[Bar]:
        instrument = self.instruments.get(str(bar_type.instrument_id))
        if instrument is None:
            return []
        bar_request = BarRequest(instrument, read_bar_period(bar_type), time_range)
        return await read_saved_bars(database_url=self.bar_store_input.database_url, bar_request=bar_request)

    @override
    async def _subscribe_bars(self, command: SubscribeBars) -> None:
        """Sends only the bars that start at the current bar period or later."""
        self.next_bar_starts[command.bar_type] = floor_to_bar_start(
            read_utc(self.clock), read_bar_period(command.bar_type)
        )

    @override
    async def _unsubscribe_bars(self, command: UnsubscribeBars) -> None:
        self.next_bar_starts.pop(command.bar_type, None)

    async def send_new_bars(self) -> None:
        """Sends the saved bars of each subscription that the strategy did not get yet, in time order."""
        for bar_type, next_bar_start in list(self.next_bar_starts.items()):
            bar_period = read_bar_period(bar_type)
            end_utc = floor_to_bar_start(read_utc(self.clock), bar_period) + bar_period.length
            if end_utc <= next_bar_start:
                continue
            bars = await self.read_bars(bar_type, TimeRange(next_bar_start, end_utc))
            for bar in bars:
                self._handle_data(convert_bar(bar, bar_type, bar_period))
            if bars and bar_type in self.next_bar_starts:
                self.next_bar_starts[bar_type] = bars[-1].start_utc + bar_period.length

    @override
    async def _request_bars(self, request: RequestBars) -> None:
        bar_type = request.bar_type
        bar_period = read_bar_period(bar_type)
        start_utc = FIRST_BAR_UTC if request.start is None else request.start
        end_utc = read_utc(self.clock) if request.end is None else request.end
        bars = await self.read_bars(bar_type, TimeRange(start_utc, end_utc)) if start_utc < end_utc else []
        if request.limit:
            bars = bars[-request.limit :]
        self._handle_response(
            BarsResponse(
                self.client_id,
                bar_type,
                [convert_bar(bar, bar_type, bar_period) for bar in bars],
                request.request_id,
                self.clock.timestamp_ns(),
                request.start_ns,
                request.end_ns,
                request.params,  # pyright: ignore[reportUnknownMemberType] - the stub has no dict types
            )
        )


class BarStoreDataClientFactory(DataClientFactory):
    """Holds the bar store input, and the created client for the caller of `send_new_bars`."""

    def __init__(self, bar_store_input: BarStoreInput) -> None:
        self.bar_store_input = bar_store_input
        self.client: BarStoreDataClient | None = None

    def create(  # pyright: ignore[reportIncompatibleMethodOverride] - an instance factory (python_adapters.md)
        self, *, name: str, config: DataClientConfig, cache: ClientCache, clock: Clock
    ) -> BarStoreDataClient:
        self.client = BarStoreDataClient(
            name=name, config=config, cache=cache, clock=clock, bar_store_input=self.bar_store_input
        )
        return self.client
