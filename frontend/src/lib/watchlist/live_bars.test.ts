// The live daily bars of /ws/watchlist-live-bars: each message changes the live bars of its instruments only.
import { describe, expect, it } from 'vite-plus/test';
import { applyWatchlistLiveBars, findWatchlistLiveBar, type WatchlistLiveBars } from './index';

const TENCENT = { symbol: '700', exchange: 'SEHK', currency: 'HKD' };
const APPLE = { symbol: 'AAPL', exchange: 'NASDAQ', currency: 'USD' };
const DAILY_BAR = { time: 1_767_312_000, open: 105, high: 107, low: 104, close: 105.5, volume: 10 };

describe('applyWatchlistLiveBars', () => {
  it('sets the live bar of each instrument in the message and keeps the others', () => {
    const first = applyWatchlistLiveBars({}, {
      type: 'live_bars',
      live_bars: [
        { ...TENCENT, bar: DAILY_BAR },
        { ...APPLE, bar: DAILY_BAR },
      ],
    });
    const second = applyWatchlistLiveBars(first, { type: 'live_bars', live_bars: [{ ...APPLE, bar: { ...DAILY_BAR, close: 106 } }] });

    expect(findWatchlistLiveBar(second, TENCENT)).toEqual(DAILY_BAR);
    expect(findWatchlistLiveBar(second, APPLE)?.close).toBe(106);
  });

  it('removes the live bar of an instrument with a null bar', () => {
    const liveBars = applyWatchlistLiveBars({}, { type: 'live_bars', live_bars: [{ ...TENCENT, bar: DAILY_BAR }] });

    const next = applyWatchlistLiveBars(liveBars, { type: 'live_bars', live_bars: [{ ...TENCENT, bar: null }] });

    expect(findWatchlistLiveBar(next, TENCENT)).toBeNull();
  });

  it('ignores other messages', () => {
    const liveBars: WatchlistLiveBars = applyWatchlistLiveBars({}, { type: 'live_bars', live_bars: [{ ...TENCENT, bar: DAILY_BAR }] });

    expect(applyWatchlistLiveBars(liveBars, { type: 'heartbeat' })).toBe(liveBars);
    expect(applyWatchlistLiveBars(liveBars, 'text')).toBe(liveBars);
  });
});
