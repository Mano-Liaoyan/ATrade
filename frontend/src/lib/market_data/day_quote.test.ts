// The last price and the change from the previous close, from the daily bars and the live bar.
import { describe, expect, it } from 'vite-plus/test';
import { formatDayChange, readDayQuote, type Bar } from './index';

const DAY_SECONDS = 86_400;

function createBar(day: number, close: number): Bar {
  return { time: day * DAY_SECONDS, open: close, high: close, low: close, close, volume: 1 };
}

describe('readDayQuote', () => {
  it('gives the last close and the change from the close of the day before', () => {
    const quote = readDayQuote([createBar(1, 100), createBar(2, 102)]);

    expect(quote).toEqual({ last: 102, change: 2, changePercent: 2 });
  });

  it('uses the close of a live bar of the last day', () => {
    const quote = readDayQuote([createBar(1, 100), createBar(2, 102)], createBar(2, 99));

    expect(quote).toEqual({ last: 99, change: -1, changePercent: -1 });
  });

  it('compares a live bar of a new day with the last bar', () => {
    const quote = readDayQuote([createBar(1, 100), createBar(2, 102)], createBar(3, 104.04));

    expect(quote?.last).toBe(104.04);
    expect(quote?.change).toBeCloseTo(2.04);
    expect(quote?.changePercent).toBeCloseTo(2);
  });

  it('has no change with only one bar, and no quote without bars', () => {
    expect(readDayQuote([createBar(1, 100)])).toEqual({ last: 100, change: null, changePercent: null });
    expect(readDayQuote([])).toBeNull();
  });
});

describe('formatDayChange', () => {
  it('shows the change and the change in percent with their signs', () => {
    expect(formatDayChange({ last: 99, change: -1, changePercent: -1 })).toBe('-1.00 (-1.00%)');
    expect(formatDayChange({ last: 102, change: 2, changePercent: 2 })).toBe('+2.00 (+2.00%)');
  });

  it('shows a dash without a change', () => {
    expect(formatDayChange({ last: 100, change: null, changePercent: null })).toBe('–');
  });
});
