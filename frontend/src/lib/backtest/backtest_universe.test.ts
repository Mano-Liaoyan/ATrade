// The universe of a multi-instrument backtest: the header label and the check of N (backtest.md 10.10.6, 10.10.7).
import { describe, expect, it } from 'vite-plus/test';
import {
  checkTopN,
  formatPeriodCountHeader,
  formatUniverseLabel,
  formatUniverseRange,
  makeScreenUniverseFields,
} from './backtest_universe';

const NO_SCREEN = { universe_screen: null, universe_rebalance_period: null } as const;
const SCREEN = { screen_id: 7, name: 'Momentum leaders', market: 'US', definition: {} };

describe('formatUniverseLabel', () => {
  it('names a rule universe by its N', () => {
    expect(formatUniverseLabel({ universe_kind: 'rule', universe_top_n: 500, ...NO_SCREEN }, 0)).toBe('Top 500 by trading value');
  });

  it('names a list universe with its instrument count: the watchlist or a screen result', () => {
    expect(formatUniverseLabel({ universe_kind: 'list', universe_top_n: null, ...NO_SCREEN }, 12)).toBe(
      'Fixed list (12)',
    );
  });

  it('names a screen universe by the screen copy and the rebalance period', () => {
    const backtest = { universe_kind: 'screen', universe_top_n: null, universe_screen: SCREEN } as const;
    expect(formatUniverseLabel({ ...backtest, universe_rebalance_period: 'quarter' }, 30)).toBe(
      'Screen Momentum leaders, each quarter',
    );
    expect(formatUniverseLabel({ ...backtest, universe_rebalance_period: 'month' }, 30)).toBe(
      'Screen Momentum leaders, each month',
    );
  });

  it('has no label for a single-instrument backtest', () => {
    expect(formatUniverseLabel({ universe_kind: 'single', universe_top_n: null, ...NO_SCREEN }, 0)).toBeUndefined();
  });
});

describe('checkTopN', () => {
  it('accepts a whole number from 1 to 500', () => {
    expect(checkTopN('1')).toEqual({ kind: 'ok', value: 1 });
    expect(checkTopN('500')).toEqual({ kind: 'ok', value: 500 });
  });

  it('gives the reason for any other N', () => {
    for (const text of ['0', '501', '2.5', '', 'ten']) {
      expect(checkTopN(text)).toEqual({ kind: 'refused', reason: 'N must be a whole number from 1 to 500.' });
    }
  });
});

describe('formatUniverseRange', () => {
  it('gives the first and the last day with universe data', () => {
    expect(formatUniverseRange({ first_day_utc: '2018-07-02T00:00:00Z', last_day_utc: '2026-10-01T00:00:00Z' })).toBe(
      'Universe data 2018-07-02 to 2026-10-01',
    );
  });

  it('says when there is no universe data', () => {
    expect(formatUniverseRange({ first_day_utc: null, last_day_utc: null })).toBe('No universe data');
    expect(formatUniverseRange(null)).toBe('No universe data');
  });
});

describe('formatPeriodCountHeader', () => {
  it('counts months for a monthly screen universe and quarters for the other universes', () => {
    expect(formatPeriodCountHeader({ universe_rebalance_period: 'month' })).toBe('Months');
    expect(formatPeriodCountHeader({ universe_rebalance_period: 'quarter' })).toBe('Quarters');
    expect(formatPeriodCountHeader({ universe_rebalance_period: null })).toBe('Quarters');
  });
});

describe('makeScreenUniverseFields', () => {
  it('reruns the screen at each period start', () => {
    expect(makeScreenUniverseFields({ mode: 'rerun', screenId: 7, rebalancePeriod: 'month', screenResultId: 3, symbols: null })).toEqual({
      universe_kind: 'screen',
      screen_id: 7,
      rebalance_period: 'month',
    });
  });

  it('takes all rows or the selected rows of a screen result as a fixed list', () => {
    const fixed = { mode: 'fixed', screenId: 7, rebalancePeriod: 'quarter', screenResultId: 3 } as const;
    expect(makeScreenUniverseFields({ ...fixed, symbols: null })).toEqual({ universe_kind: 'list', screen_result_id: 3 });
    expect(makeScreenUniverseFields({ ...fixed, symbols: ['AAA'] })).toEqual({
      universe_kind: 'list',
      screen_result_id: 3,
      symbols: ['AAA'],
    });
  });

  it('has no fixed list without a screen result', () => {
    expect(makeScreenUniverseFields({ mode: 'fixed', screenId: 7, rebalancePeriod: 'quarter', screenResultId: null, symbols: null })).toBeNull();
  });
});
