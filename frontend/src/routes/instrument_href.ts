// The href of the instrument page of a watchlist instrument: /instruments/<exchange>/<symbol>?currency=<currency>.
// The home page watchlist and the command palette use it. The watchlist column of the instrument page adds the bar
// period of the open chart, so the next instrument opens with the same bar period.
import { resolve } from '$app/paths';
import type { WatchlistInstrument } from '#lib/watchlist';

export function createInstrumentHref(instrument: WatchlistInstrument, barPeriod?: string): string {
  const instrumentPath = resolve('/instruments/[exchange]/[symbol]', {
    exchange: instrument.exchange,
    symbol: instrument.symbol,
  });
  const searchParameters = new URLSearchParams({ currency: instrument.currency });
  if (barPeriod !== undefined) {
    searchParameters.set('bar_period', barPeriod);
  }
  return `${instrumentPath}?${searchParameters.toString()}`;
}
