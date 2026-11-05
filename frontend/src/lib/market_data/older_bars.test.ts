// Older bars of the instrument page chart: the range before the first bar, the join, and when the chart asks.
import { describe, expect, it } from 'vite-plus/test';
import { BAR_PERIODS } from './bars';
import { countPrependedBars, findOlderBarsRange, isMoveToFirstBar, OLDER_BARS_RANGE_DAYS, prependOlderBars, readOlderBars } from './older_bars';
import { MAX_BARS_PER_REQUEST } from './run_bars';
import { BAR_PERIOD_SECONDS } from './trade_marks';

const TENCENT = { symbol: '700', exchange: 'SEHK', currency: 'HKD' };
// 2023-01-02 00:00 UTC.
const FIRST_TIME = 1672617600;
const DAY = 86_400;

function bar(time: number): { time: number; open: number; high: number; low: number; close: number; volume: number } {
  return { time, open: 1, high: 2, low: 0.5, close: 1.5, volume: 10 };
}

describe('findOlderBarsRange', () => {
  it('ends at the first bar and starts the range length of the bar period before it', () => {
    expect(findOlderBarsRange(FIRST_TIME, '1-DAY')).toEqual({ startUtc: '2020-01-02T00:00:00.000Z', endUtc: '2023-01-02T00:00:00.000Z' });
    expect(findOlderBarsRange(FIRST_TIME, '1-MINUTE')).toEqual({ startUtc: '2022-12-26T00:00:00.000Z', endUtc: '2023-01-02T00:00:00.000Z' });
  });

  it('keeps each range of each bar period within the bar limit of the route', () => {
    for (const { value } of BAR_PERIODS) {
      expect((OLDER_BARS_RANGE_DAYS[value] * DAY) / BAR_PERIOD_SECONDS[value]).toBeLessThanOrEqual(MAX_BARS_PER_REQUEST);
    }
  });
});

describe('readOlderBars', () => {
  it('sends the explicit range and drops the first bar of the chart from the answer', async () => {
    const requestedUrls: string[] = [];
    const recordingFetch: typeof fetch = (input) => {
      if (typeof input === 'string') {
        requestedUrls.push(input);
      }
      const bars = [bar(FIRST_TIME - 2 * DAY), bar(FIRST_TIME - DAY), bar(FIRST_TIME)];
      return Promise.resolve(new Response(JSON.stringify({ bars }), { status: 200 }));
    };

    const result = await readOlderBars(recordingFetch, TENCENT, '1-DAY', FIRST_TIME);

    expect(result).toEqual({ kind: 'loaded', bars: [bar(FIRST_TIME - 2 * DAY), bar(FIRST_TIME - DAY)] });
    expect(requestedUrls).toEqual([
      '/api/market-data/bars?symbol=700&exchange=SEHK&currency=HKD&bar_period=1-DAY' +
        '&start_utc=2020-01-02T00%3A00%3A00.000Z&end_utc=2023-01-02T00%3A00%3A00.000Z',
    ]);
  });

  it('returns the failure of the route', async () => {
    const failingFetch: typeof fetch = () => Promise.resolve(new Response(JSON.stringify({ detail: 'IB Gateway is not reachable.' }), { status: 503 }));

    expect(await readOlderBars(failingFetch, TENCENT, '1-DAY', FIRST_TIME)).toEqual({ kind: 'failed', message: 'IB Gateway is not reachable.' });
  });
});

describe('prependOlderBars', () => {
  it('puts the older bars before the bars without a bar 2 times', () => {
    const bars = [bar(FIRST_TIME), bar(FIRST_TIME + DAY)];

    expect(prependOlderBars([bar(FIRST_TIME - DAY), bar(FIRST_TIME)], bars)).toEqual([bar(FIRST_TIME - DAY), ...bars]);
  });

  it('keeps all older bars when the chart has no bars', () => {
    expect(prependOlderBars([bar(FIRST_TIME)], [])).toEqual([bar(FIRST_TIME)]);
  });
});

describe('countPrependedBars', () => {
  const bars = [bar(FIRST_TIME), bar(FIRST_TIME + DAY)];

  it('counts the bars before the previous bars', () => {
    expect(countPrependedBars(bars, [bar(FIRST_TIME - 2 * DAY), bar(FIRST_TIME - DAY), ...bars])).toBe(2);
  });

  it('is null for new bars, the same bars, or no previous bars', () => {
    expect(countPrependedBars(bars, [bar(FIRST_TIME + 2 * DAY), bar(FIRST_TIME + 3 * DAY), bar(FIRST_TIME + 4 * DAY)])).toBeNull();
    expect(countPrependedBars(bars, [...bars])).toBeNull();
    expect(countPrependedBars([], bars)).toBeNull();
  });

  it('is null when the last bar is not the same', () => {
    expect(countPrependedBars(bars, [bar(FIRST_TIME - DAY), bar(FIRST_TIME), bar(FIRST_TIME + 2 * DAY)])).toBeNull();
  });
});

describe('isMoveToFirstBar', () => {
  it('is true only for a move to the left that comes near the first bar', () => {
    expect(isMoveToFirstBar(12, 8)).toBe(true);
    expect(isMoveToFirstBar(-3, -5)).toBe(true);
    expect(isMoveToFirstBar(8, 12)).toBe(false);
    expect(isMoveToFirstBar(40, 20)).toBe(false);
    expect(isMoveToFirstBar(null, 0)).toBe(false);
  });
});
