// The universe of a multi-instrument backtest (docs/architecture/backtest.md sections 10.10.6 and 10.10.7).

import type { Backtest, UsUniverseRange } from './backtest_api';

export const MAX_TOP_N = 500;
const UTC_DATE_LENGTH = 'YYYY-MM-DD'.length;

export type TopNCheck = { kind: 'ok'; value: number } | { kind: 'refused'; reason: string };

// The header line shows the universe in place of the instrument symbol. A `list` universe is the watchlist.
export function formatUniverseLabel(
  backtest: Pick<Backtest, 'universe_kind' | 'universe_top_n'>,
  instrumentCount: number,
): string | undefined {
  if (backtest.universe_kind === 'rule') {
    return `Top ${String(backtest.universe_top_n)} by trading value`;
  }
  if (backtest.universe_kind === 'list') {
    return `Watchlist (${String(instrumentCount)})`;
  }
  return undefined;
}

export function checkTopN(text: string): TopNCheck {
  const value = Number(text);
  if (text.trim() === '' || !Number.isInteger(value) || value < 1 || value > MAX_TOP_N) {
    return { kind: 'refused', reason: `N must be a whole number from 1 to ${String(MAX_TOP_N)}.` };
  }
  return { kind: 'ok', value };
}

// The first and the last day with universe data, as UTC dates.
export function formatUniverseRange(range: UsUniverseRange | null): string {
  if (range?.first_day_utc == null || range.last_day_utc == null) {
    return 'No universe data';
  }
  return `Universe data ${range.first_day_utc.slice(0, UTC_DATE_LENGTH)} to ${range.last_day_utc.slice(0, UTC_DATE_LENGTH)}`;
}
