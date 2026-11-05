// The live daily bars of /ws/watchlist-live-bars: the current daily bar of each watchlist instrument from IBKR
// (docs/architecture/market_data.md section 8.5.1). The message types come from the backend message models.
import type { components } from '#lib/api';
import { readSocketMessage } from '#lib/foundation/live_socket';
import { formatWatchlistInstrument, type InstrumentToAdd } from './watchlist_api';

type WatchlistLiveBarsMessage = components['schemas']['WatchlistLiveBarsMessage'];
type LiveBar = components['schemas']['BarResponse'];

// The live bars by instrument name ("700 / SEHK / HKD").
export type WatchlistLiveBars = Readonly<Record<string, LiveBar>>;

export const WATCHLIST_LIVE_BARS_SOCKET_PATH = '/ws/watchlist-live-bars';

/** The live bars after a message: a bar replaces the live bar of its instrument, and null removes it. */
export function applyWatchlistLiveBars(liveBars: WatchlistLiveBars, message: unknown): WatchlistLiveBars {
  const liveBarsMessage = readSocketMessage<WatchlistLiveBarsMessage>(message, ['live_bars']);
  if (liveBarsMessage === null) {
    return liveBars;
  }
  const changes = new Map(liveBarsMessage.live_bars.map(({ bar, ...instrument }) => [formatWatchlistInstrument(instrument), bar]));
  const kept = Object.entries(liveBars).filter(([name]) => !changes.has(name));
  const changed = [...changes].filter((entry): entry is [string, LiveBar] => entry[1] !== null);
  return Object.fromEntries([...kept, ...changed]);
}

export function findWatchlistLiveBar(liveBars: WatchlistLiveBars, instrument: InstrumentToAdd): LiveBar | null {
  return liveBars[formatWatchlistInstrument(instrument)] ?? null;
}
