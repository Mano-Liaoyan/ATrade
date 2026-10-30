// The universe of a multi-instrument backtest (docs/architecture/backtest.md sections 10.10.6 and 10.10.7).

import type { Backtest, BacktestRequest, UsUniverseRange } from './backtest_api';

export const MAX_TOP_N = 500;
const UTC_DATE_LENGTH = 'YYYY-MM-DD'.length;

export type TopNCheck = { kind: 'ok'; value: number } | { kind: 'refused'; reason: string };

export type RebalancePeriod = NonNullable<Backtest['universe_rebalance_period']>;

// The header line shows the universe in place of the instrument symbol. A `list` universe is the watchlist or a
// screen result (decided in #208), so its label names neither.
export function formatUniverseLabel(
  backtest: Pick<Backtest, 'universe_kind' | 'universe_top_n' | 'universe_screen' | 'universe_rebalance_period'>,
  instrumentCount: number,
): string | undefined {
  if (backtest.universe_kind === 'rule') {
    return `Top ${String(backtest.universe_top_n)} by trading value`;
  }
  if (backtest.universe_kind === 'list') {
    return `Fixed list (${String(instrumentCount)})`;
  }
  if (backtest.universe_kind === 'screen' && backtest.universe_screen !== null) {
    return `Screen ${backtest.universe_screen.name}, each ${backtest.universe_rebalance_period ?? 'quarter'}`;
  }
  return undefined;
}

// The Instruments tab counts the universe periods of each member: months for a monthly `screen` universe.
export function formatPeriodCountHeader(backtest: Pick<Backtest, 'universe_rebalance_period'>): string {
  return backtest.universe_rebalance_period === 'month' ? 'Months' : 'Quarters';
}

// What the buttons of the screen page give the "New backtest" form: the screen, the screen result, and the selected
// rows (null: all rows).
export interface ScreenSource {
  screenId: number;
  screenResultId: number;
  symbols: string[] | null;
}

export interface ScreenUniverseSource {
  // `rerun`: the screen runs again at each period start. `fixed`: the rows of one screen result.
  mode: 'rerun' | 'fixed';
  screenId: number;
  rebalancePeriod: RebalancePeriod;
  screenResultId: number | null;
  // Only these rows of the screen result. Null: all rows.
  symbols: string[] | null;
}

export type ScreenUniverseFields = Pick<
  BacktestRequest,
  'universe_kind' | 'screen_id' | 'rebalance_period' | 'screen_result_id' | 'symbols'
>;

// The universe fields of the start request (docs/architecture/backtest.md section 10.10.6). Null for a fixed list
// without a screen result.
export function makeScreenUniverseFields(source: ScreenUniverseSource): ScreenUniverseFields | null {
  if (source.mode === 'rerun') {
    return { universe_kind: 'screen', screen_id: source.screenId, rebalance_period: source.rebalancePeriod };
  }
  if (source.screenResultId === null) {
    return null;
  }
  return {
    universe_kind: 'list',
    screen_result_id: source.screenResultId,
    ...(source.symbols === null ? {} : { symbols: source.symbols }),
  };
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
