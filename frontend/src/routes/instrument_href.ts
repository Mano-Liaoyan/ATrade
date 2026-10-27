// The href of the instrument page of a watchlist instrument: /instruments/<exchange>/<symbol>?currency=<currency>.
// The home page watchlist and the command palette use it.
import { resolve } from '$app/paths';
import type { WatchlistInstrument } from '#lib/watchlist';

export function createInstrumentHref(instrument: WatchlistInstrument): string {
  const instrumentPath = resolve('/instruments/[exchange]/[symbol]', {
    exchange: instrument.exchange,
    symbol: instrument.symbol,
  });
  const searchParameters = new URLSearchParams({ currency: instrument.currency });
  return `${instrumentPath}?${searchParameters.toString()}`;
}
