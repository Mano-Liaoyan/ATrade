// The bars and the indicator values of a long backtest or forward test range, read in windows that the routes accept.
import { describe, expect, it } from 'vite-plus/test';
import type { Bar } from './bars';
import type { IndicatorSeriesResult } from './indicator_series';
import { MAX_BARS_PER_REQUEST, readRunBars, readRunIndicatorSeries, splitTimeRange } from './run_bars';

const MSFT = { symbol: 'MSFT', exchange: 'NASDAQ', currency: 'USD' };
const MINUTE = 60;
const WINDOW_SECONDS = MAX_BARS_PER_REQUEST * MINUTE;
const START = Date.parse('2026-01-05T00:00:00Z') / 1000;

function makeBar(time: number): Bar {
  return { time, open: 1, high: 2, low: 0.5, close: 1.5, volume: 10 };
}

function toIso(unixSeconds: number): string {
  return new Date(unixSeconds * 1000).toISOString();
}

describe('splitTimeRange', () => {
  it('keeps a range of at most the bar limit in one window', () => {
    expect(splitTimeRange(START, START + WINDOW_SECONDS, '1-MINUTE')).toEqual([{ start: START, end: START + WINDOW_SECONDS }]);
  });

  it('splits a longer range into consecutive windows of the bar limit', () => {
    const end = START + 2 * WINDOW_SECONDS + 5 * MINUTE;

    expect(splitTimeRange(START, end, '1-MINUTE')).toEqual([
      { start: START, end: START + WINDOW_SECONDS },
      { start: START + WINDOW_SECONDS, end: START + 2 * WINDOW_SECONDS },
      { start: START + 2 * WINDOW_SECONDS, end },
    ]);
  });

  it('uses the length of the bar period', () => {
    const day = 86_400;

    expect(splitTimeRange(START, START + 3 * 365 * day, '1-DAY')).toHaveLength(1);
  });
});

describe('readRunBars', () => {
  it('reads a 1 minute range of 30 days in windows and joins the bars without duplicates', async () => {
    const requestedUrls: URL[] = [];
    const fetchFunction: typeof fetch = (input) => {
      const url = new URL(input as string, 'http://atrade');
      requestedUrls.push(url);
      const start = Date.parse(url.searchParams.get('start_utc') ?? '') / 1000;
      // Each answer has the first bar of its window and the bar before it (as a widened range would have).
      return Promise.resolve(new Response(JSON.stringify({ bars: [makeBar(start - MINUTE), makeBar(start)] }), { status: 200 }));
    };
    const end = START + 30 * 86_400;

    const result = await readRunBars(fetchFunction, MSFT, '1-MINUTE', { startUtc: toIso(START), endUtc: toIso(end), sourceOrder: ['databento'] });

    expect(requestedUrls.map((url) => [url.searchParams.get('start_utc'), url.searchParams.get('end_utc')])).toEqual([
      [toIso(START), toIso(START + WINDOW_SECONDS)],
      [toIso(START + WINDOW_SECONDS), toIso(START + 2 * WINDOW_SECONDS)],
      [toIso(START + 2 * WINDOW_SECONDS), toIso(end)],
    ]);
    expect(requestedUrls.every((url) => url.searchParams.getAll('source_order').join() === 'databento')).toBe(true);
    expect(result.kind === 'loaded' && result.bars.map((bar) => bar.time)).toEqual([
      START - MINUTE,
      START,
      START + WINDOW_SECONDS - MINUTE,
      START + WINDOW_SECONDS,
      START + 2 * WINDOW_SECONDS - MINUTE,
      START + 2 * WINDOW_SECONDS,
    ]);
  });

  it('reads a running forward test range up to now and sends no end in the last window', async () => {
    const requestedUrls: URL[] = [];
    const fetchFunction: typeof fetch = (input) => {
      requestedUrls.push(new URL(input as string, 'http://atrade'));
      return Promise.resolve(new Response(JSON.stringify({ bars: [] }), { status: 200 }));
    };
    const now = START + WINDOW_SECONDS + 10 * MINUTE;

    await readRunBars(fetchFunction, MSFT, '1-MINUTE', { startUtc: toIso(START) }, now * 1000);

    expect(requestedUrls.map((url) => [url.searchParams.get('start_utc'), url.searchParams.get('end_utc')])).toEqual([
      [toIso(START), toIso(START + WINDOW_SECONDS)],
      [toIso(START + WINDOW_SECONDS), null],
    ]);
  });

  it('fails with the message of the first failed window', async () => {
    let count = 0;
    const fetchFunction: typeof fetch = () => {
      count += 1;
      return Promise.resolve(
        count === 1
          ? new Response(JSON.stringify({ bars: [] }), { status: 200 })
          : new Response(JSON.stringify({ detail: 'IB Gateway is not reachable.' }), { status: 503 }),
      );
    };

    const result = await readRunBars(fetchFunction, MSFT, '1-MINUTE', { startUtc: toIso(START), endUtc: toIso(START + 2 * WINDOW_SECONDS) });

    expect(result).toEqual({ kind: 'failed', message: 'IB Gateway is not reachable.' });
  });
});

describe('readRunIndicatorSeries', () => {
  it('reads the values in windows and joins the times and the outputs', async () => {
    const bodies: { start_utc: string; end_utc: string }[] = [];
    const fetchFunction: typeof fetch = (_input, init) => {
      const body = JSON.parse(init?.body as string) as { start_utc: string; end_utc: string };
      bodies.push(body);
      const start = Date.parse(body.start_utc) / 1000;
      const answer: IndicatorSeriesResult = {
        times: [start - MINUTE, start],
        series: [{ indicator: 'sma', parameters: { period: 20 }, outputs: { value: [start - MINUTE, start] } }],
      };
      return Promise.resolve(new Response(JSON.stringify(answer), { status: 200 }));
    };
    const lastBarTime = START + WINDOW_SECONDS + 10 * MINUTE;

    const result = await readRunIndicatorSeries(fetchFunction, {
      instrument: MSFT,
      barPeriod: '1-MINUTE',
      firstBarTime: START,
      lastBarTime,
      indicators: [{ indicator: 'sma', parameters: { period: 20 } }],
    });

    expect(bodies.map((body) => [body.start_utc, body.end_utc])).toEqual([
      [toIso(START), toIso(START + WINDOW_SECONDS)],
      [toIso(START + WINDOW_SECONDS), toIso(lastBarTime + 1)],
    ]);
    const times = [START - MINUTE, START, START + WINDOW_SECONDS - MINUTE, START + WINDOW_SECONDS];
    expect(result).toEqual({
      kind: 'ok',
      value: { times, series: [{ indicator: 'sma', parameters: { period: 20 }, outputs: { value: times } }] },
    });
  });
});
