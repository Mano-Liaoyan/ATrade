// Calls GET /api/market-data/bars and reads the chart instrument and bar period from the instrument page URL.
import { describe, expect, it } from 'vitest';
import { formatChartSearch, readBars, readChartRequest } from './index';

const TENCENT = { symbol: '700', exchange: 'SEHK', currency: 'HKD' };
const BAR = { time: 1767225600, open: 146, high: 148, low: 145, close: 146.5, volume: 1000 };

function respondWith(status: number, body: unknown): typeof fetch {
  return () => Promise.resolve(new Response(JSON.stringify(body), { status }));
}

describe('readBars', () => {
  it('returns the bars that the backend sends', async () => {
    const barsResult = await readBars(respondWith(200, { bars: [BAR] }), TENCENT, '1-HOUR');

    expect(barsResult).toEqual({ kind: 'loaded', bars: [BAR] });
  });

  it('sends the instrument and the bar period in the URL', async () => {
    const requestedUrls: string[] = [];
    const recordingFetch: typeof fetch = (input) => {
      if (typeof input === 'string') {
        requestedUrls.push(input);
      }
      return Promise.resolve(new Response(JSON.stringify({ bars: [] }), { status: 200 }));
    };

    await readBars(recordingFetch, { symbol: 'BRK B', exchange: 'NYSE', currency: 'USD' }, '1-DAY');

    expect(requestedUrls).toEqual(['/api/market-data/bars?symbol=BRK+B&exchange=NYSE&currency=USD&bar_period=1-DAY']);
  });

  it('shows the backend message when IB Gateway is not reachable', async () => {
    const detail = 'IB Gateway is not reachable at ib-gateway:4004. Bars that are not saved need IB Gateway.';

    const barsResult = await readBars(respondWith(503, { detail }), TENCENT, '1-HOUR');

    expect(barsResult).toEqual({ kind: 'failed', message: detail });
  });

  it('says that the backend is not reachable when the request fails', async () => {
    const failingFetch: typeof fetch = () => Promise.reject(new TypeError('Failed to fetch'));

    const barsResult = await readBars(failingFetch, TENCENT, '1-HOUR');

    expect(barsResult).toEqual({ kind: 'failed', message: 'Backend not reachable. The bars did not load.' });
  });

  it('names the HTTP status when a proxy answers without a message', async () => {
    const barsResult = await readBars(respondWith(504, 'Gateway Timeout'), TENCENT, '1-HOUR');

    expect(barsResult).toEqual({ kind: 'failed', message: 'Reading the bars failed with HTTP status 504.' });
  });
});

describe('readChartRequest', () => {
  it('reads the instrument from the route and the bar period from the URL', () => {
    const searchParameters = new URLSearchParams('currency=HKD&bar_period=5-MINUTE');

    const chartRequest = readChartRequest({ exchange: 'SEHK', symbol: '700' }, searchParameters);

    expect(chartRequest).toEqual({ instrument: TENCENT, barPeriod: '5-MINUTE' });
  });

  it('uses daily bars when the URL has no bar period or an unknown one', () => {
    const route = { exchange: 'SEHK', symbol: '700' };

    expect(readChartRequest(route, new URLSearchParams('currency=HKD'))).toEqual({ instrument: TENCENT, barPeriod: '1-DAY' });
    expect(readChartRequest(route, new URLSearchParams('currency=HKD&bar_period=1-WEEK'))).toEqual({
      instrument: TENCENT,
      barPeriod: '1-DAY',
    });
  });

  it('returns null when the URL does not name a complete instrument', () => {
    expect(readChartRequest({ exchange: 'SEHK', symbol: '700' }, new URLSearchParams(''))).toBeNull();
    expect(readChartRequest({ symbol: '700' }, new URLSearchParams('currency=HKD'))).toBeNull();
  });
});

describe('formatChartSearch', () => {
  it('writes the URL search that readChartRequest reads', () => {
    const chartSearch = formatChartSearch({ instrument: TENCENT, barPeriod: '1-HOUR' });

    expect(chartSearch).toBe('currency=HKD&bar_period=1-HOUR');
    expect(readChartRequest({ exchange: 'SEHK', symbol: '700' }, new URLSearchParams(chartSearch))).toEqual({
      instrument: TENCENT,
      barPeriod: '1-HOUR',
    });
  });
});
