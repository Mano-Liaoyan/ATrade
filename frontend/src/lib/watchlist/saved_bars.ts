// The saved bars of watchlist instruments. The backtest form offers only instruments with saved bars of the selected
// bar period, because a backtest reads only saved bars (docs/architecture/backtest.md section 10.1).
import type { components } from '#lib/api';
import { formatUtcTime } from '#lib/foundation/time_format';
import type { WatchlistInstrument } from './watchlist_api';

export type SavedBars = components['schemas']['SavedBarsResponse'];
type BarPeriod = components['schemas']['BarPeriod'];

export function findSavedBars(instrument: WatchlistInstrument, barPeriod: BarPeriod): SavedBars | undefined {
  return instrument.saved_bars.find((savedBars) => savedBars.bar_period === barPeriod);
}

export function selectInstrumentsWithSavedBars(
  instruments: WatchlistInstrument[],
  barPeriod: BarPeriod,
): WatchlistInstrument[] {
  return instruments.filter((instrument) => findSavedBars(instrument, barPeriod) !== undefined);
}

export function describeSavedBars(savedBars: SavedBars): string {
  return `Saved bars start from ${formatUtcTime(savedBars.first_start_utc)} to ${formatUtcTime(savedBars.last_start_utc)}.`;
}
