// The backtest form offers only watchlist instruments with saved bars of the selected bar period.
import { describe, expect, it } from 'vitest';
import { describeSavedBars, findSavedBars, selectInstrumentsWithSavedBars, type WatchlistInstrument } from './index';

const DAILY_BARS = {
  bar_period: '1-DAY',
  first_start_utc: '2023-01-02T00:00:00Z',
  last_start_utc: '2025-12-31T00:00:00Z',
} as const;
const HOURLY_BARS = {
  bar_period: '1-HOUR',
  first_start_utc: '2026-03-02T14:00:00Z',
  last_start_utc: '2026-03-03T20:00:00Z',
} as const;
const APPLE: WatchlistInstrument = {
  id: 1,
  symbol: 'AAPL',
  exchange: 'NASDAQ',
  currency: 'USD',
  added_at_utc: '2026-01-02T03:04:05Z',
  saved_bars: [HOURLY_BARS, DAILY_BARS],
};
const MICROSOFT: WatchlistInstrument = {
  id: 2,
  symbol: 'MSFT',
  exchange: 'NASDAQ',
  currency: 'USD',
  added_at_utc: '2026-01-02T03:04:05Z',
  saved_bars: [HOURLY_BARS],
};
const TENCENT: WatchlistInstrument = {
  id: 3,
  symbol: '700',
  exchange: 'SEHK',
  currency: 'HKD',
  added_at_utc: '2026-01-02T03:04:05Z',
  saved_bars: [],
};

describe('selectInstrumentsWithSavedBars', () => {
  it('keeps the instruments with saved bars of the bar period, in the watchlist order', () => {
    expect(selectInstrumentsWithSavedBars([APPLE, MICROSOFT, TENCENT], '1-HOUR')).toEqual([APPLE, MICROSOFT]);
    expect(selectInstrumentsWithSavedBars([APPLE, MICROSOFT, TENCENT], '1-DAY')).toEqual([APPLE]);
  });

  it('returns no instrument when no instrument has saved bars of the bar period', () => {
    expect(selectInstrumentsWithSavedBars([APPLE, MICROSOFT, TENCENT], '1-MINUTE')).toEqual([]);
  });
});

describe('findSavedBars', () => {
  it('returns the saved bars of the bar period, or undefined', () => {
    expect(findSavedBars(APPLE, '1-DAY')).toEqual(DAILY_BARS);
    expect(findSavedBars(MICROSOFT, '1-DAY')).toBeUndefined();
  });
});

describe('describeSavedBars', () => {
  it('names the first and the last saved bar in UTC', () => {
    expect(describeSavedBars(DAILY_BARS)).toBe('Saved bars start from 2023-01-02 00:00:00 UTC to 2025-12-31 00:00:00 UTC.');
  });
});
