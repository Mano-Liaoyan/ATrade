// The universe of a multi-instrument backtest: the header label and the check of N (backtest.md 10.10.6, 10.10.7).
import { describe, expect, it } from 'vite-plus/test';
import { checkTopN, formatUniverseLabel, formatUniverseRange } from './backtest_universe';

describe('formatUniverseLabel', () => {
  it('names a rule universe by its N', () => {
    expect(formatUniverseLabel({ universe_kind: 'rule', universe_top_n: 500 }, 0)).toBe('Top 500 by trading value');
  });

  it('names a list universe with its instrument count', () => {
    expect(formatUniverseLabel({ universe_kind: 'list', universe_top_n: null }, 12)).toBe('Watchlist (12)');
  });

  it('has no label for a single-instrument backtest', () => {
    expect(formatUniverseLabel({ universe_kind: 'single', universe_top_n: null }, 0)).toBeUndefined();
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
