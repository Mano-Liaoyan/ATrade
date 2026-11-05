// The last price and the change from the previous close, from the daily bars and the live bar.
import { describe, expect, it } from 'vite-plus/test';
import { formatDayChange, readDayQuote, readLatestQuote, writeLatestQuote, type Bar } from './index';

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

  it('compares a live bar of a new day with the close of the last day, not with the day before', () => {
    // NVDA on 2026-11-05: the last daily bar closed at 200.13, the day before at 206.69, the live bar is at 184.48.
    const quote = readDayQuote([createBar(1, 206.69), createBar(2, 200.13)], createBar(3, 184.48));

    expect(quote?.last).toBe(184.48);
    expect(quote?.change).toBeCloseTo(-15.65);
    expect(quote?.changePercent).toBeCloseTo(-7.82);
  });

  it('compares an intraday live bar with the close of the day before its day', () => {
    const fifteenHours = 15 * 3600;
    const newDay = readDayQuote([createBar(1, 100), createBar(2, 102)], { ...createBar(3, 99), time: 3 * DAY_SECONDS + fifteenHours });
    const lastDay = readDayQuote([createBar(1, 100), createBar(2, 102)], { ...createBar(2, 99), time: 2 * DAY_SECONDS + fifteenHours });

    expect(newDay).toEqual({ last: 99, change: -3, changePercent: (-3 / 102) * 100 });
    expect(lastDay).toEqual({ last: 99, change: -1, changePercent: -1 });
  });

  it('does not use a live bar older than the last daily bar', () => {
    const quote = readDayQuote([createBar(1, 100), createBar(2, 102)], createBar(1, 90));

    expect(quote).toEqual({ last: 102, change: 2, changePercent: 2 });
  });

  it('has no change with only one bar, and no quote without bars', () => {
    expect(readDayQuote([createBar(1, 100)])).toEqual({ last: 100, change: null, changePercent: null });
    expect(readDayQuote([])).toBeNull();
  });
});

describe('formatDayChange', () => {
  it('shows the change and the change in percent with their signs', () => {
    expect(formatDayChange({ last: 99, change: -1, changePercent: -1 })).toBe('-1.00 (-1.00 %)');
    expect(formatDayChange({ last: 102, change: 2, changePercent: 2 })).toBe('+2.00 (+2.00 %)');
  });

  it('shows a dash without a change', () => {
    expect(formatDayChange({ last: 100, change: null, changePercent: null })).toBe('–');
  });
});

// The map is one for the module, so each test uses its own instrument.
describe('writeLatestQuote', () => {
  const DAILY_BARS = [createBar(1, 100), createBar(2, 102)];

  it('writes the quote of the daily bars only when the instrument has no quote', () => {
    const instrument = { symbol: 'DAILY', exchange: 'ARCA', currency: 'USD' };
    expect(readLatestQuote(instrument)).toBeNull();

    writeLatestQuote(instrument, DAILY_BARS, null);

    expect(readLatestQuote(instrument)).toEqual({ last: 102, change: 2, changePercent: 2 });
  });

  it('keeps one quote through a click on the row, the open page, and a move to another page', () => {
    const instrument = { symbol: 'CLICK', exchange: 'ARCA', currency: 'USD' };
    // Before the click: the watchlist live bar.
    writeLatestQuote(instrument, DAILY_BARS, createBar(3, 104.04));
    const beforeClick = readLatestQuote(instrument);
    expect(beforeClick?.last).toBe(104.04);

    // The open page: its daily bars arrive before its own live bar. The quote stays the live quote.
    writeLatestQuote(instrument, DAILY_BARS, null);
    expect(readLatestQuote(instrument)).toEqual(beforeClick);

    // The live bar of the page replaces the quote, and the quote stays after the user leaves the page.
    writeLatestQuote(instrument, DAILY_BARS, createBar(3, 105.06));
    expect(readLatestQuote(instrument)?.last).toBe(105.06);
    writeLatestQuote(instrument, DAILY_BARS, null);
    expect(readLatestQuote(instrument)?.last).toBe(105.06);
  });
});
