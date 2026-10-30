// The saved bars of watchlist instruments. The backtest form offers only instruments with saved bars of the selected
// bar period, because a backtest reads only saved bars (docs/architecture/backtest.md section 10.1).
import type { components } from '#lib/api';
import { formatUtcTime } from '#lib/foundation/time_format';
import type { WatchlistInstrument } from './watchlist_api';

type BarPeriod = components['schemas']['BarPeriod'];
// The first and the last saved bar of one bar period, over all bar sources.
export type SavedBars = Pick<components['schemas']['SavedBarsResponse'], 'first_start_utc' | 'last_start_utc'>;

export function findSavedBars(instrument: WatchlistInstrument, barPeriod: BarPeriod): SavedBars | undefined {
  // The times are UTC ISO texts of the same format, so the text order is the time order.
  return instrument.saved_bars
    .filter((savedBars) => savedBars.bar_period === barPeriod)
    .reduce<SavedBars | undefined>(
      (span, savedBars) => ({
        first_start_utc:
          span === undefined || savedBars.first_start_utc < span.first_start_utc
            ? savedBars.first_start_utc
            : span.first_start_utc,
        last_start_utc:
          span === undefined || savedBars.last_start_utc > span.last_start_utc ? savedBars.last_start_utc : span.last_start_utc,
      }),
      undefined,
    );
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
