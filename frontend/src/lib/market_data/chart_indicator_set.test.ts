// The chart indicator set (indicator.md section 23.9.7): the read, the save, and the favorites of "Add indicator".
import { describe, expect, it } from 'vite-plus/test';
import { orderByFavorites, readChartIndicatorSet, saveChartIndicatorSet, toggleFavorite, type ChartIndicatorSet } from './chart_indicator_set';
import type { ChartIndicatorDefinition } from './chart_indicators';

interface RecordedRequest {
  url: string;
  method: string;
  body: string | null;
}

function recordRequests(status: number, body: unknown): { fetchFunction: typeof fetch; requests: RecordedRequest[] } {
  const requests: RecordedRequest[] = [];
  const fetchFunction: typeof fetch = (input, init) => {
    requests.push({
      url: typeof input === 'string' ? input : '',
      method: init?.method ?? 'GET',
      body: typeof init?.body === 'string' ? init.body : null,
    });
    return Promise.resolve(new Response(JSON.stringify(body), { status }));
  };
  return { fetchFunction, requests };
}

const SAVED_SET: ChartIndicatorSet = {
  panes: [
    { indicators: [{ indicator: 'sma', parameters: { period: 50 }, hidden: false, lines: [{ output: 'value', color: 1, style: 'solid', width: 2 }] }] },
    { indicators: [{ indicator: 'rsi', parameters: { period: 14 }, hidden: true, lines: [{ output: 'value', color: 5, style: 'dotted', width: 3 }] }] },
  ],
  favorites: ['rsi'],
};

function definition(key: string): ChartIndicatorDefinition {
  return { key, name: key.toUpperCase(), short_name: key.toUpperCase(), chart_placement: 'price', parameters: [], outputs: ['value'], value_description: '' };
}

describe('readChartIndicatorSet', () => {
  it('reads the saved set', async () => {
    const { fetchFunction, requests } = recordRequests(200, SAVED_SET);

    const result = await readChartIndicatorSet(fetchFunction);

    expect(result).toEqual({ kind: 'ok', value: SAVED_SET });
    expect(requests).toEqual([{ url: '/api/market-data/chart-indicators', method: 'GET', body: null }]);
  });
});

describe('saveChartIndicatorSet', () => {
  it('sends the whole set with PUT', async () => {
    const { fetchFunction, requests } = recordRequests(200, SAVED_SET);

    const result = await saveChartIndicatorSet(fetchFunction, SAVED_SET);

    expect(result).toEqual({ kind: 'ok', value: SAVED_SET });
    expect(requests).toEqual([{ url: '/api/market-data/chart-indicators', method: 'PUT', body: JSON.stringify(SAVED_SET) }]);
  });

  it('gives the message of the first problem of a refused set', async () => {
    const problems = [{ location: ['favorites', 0], message: "Unknown indicator 'x'." }];
    const { fetchFunction } = recordRequests(422, { problems });

    expect(await saveChartIndicatorSet(fetchFunction, SAVED_SET)).toEqual({ kind: 'failed', message: "Unknown indicator 'x'." });
  });

  it('gives the detail text of another failure', async () => {
    const { fetchFunction } = recordRequests(500, { detail: 'The database is not reachable.' });

    expect(await saveChartIndicatorSet(fetchFunction, SAVED_SET)).toEqual({ kind: 'failed', message: 'The database is not reachable.' });
  });
});

describe('toggleFavorite', () => {
  it('adds a key at the end', () => {
    expect(toggleFavorite(['rsi'], 'sma')).toEqual(['rsi', 'sma']);
  });

  it('removes a favorite key', () => {
    expect(toggleFavorite(['rsi', 'sma', 'ema'], 'sma')).toEqual(['rsi', 'ema']);
  });
});

describe('orderByFavorites', () => {
  const catalog = ['sma', 'ema', 'rsi', 'macd'].map(definition);

  it('puts the favorites first, then the others, each in catalog order', () => {
    expect(orderByFavorites(catalog, ['macd', 'ema']).map((item) => item.key)).toEqual(['ema', 'macd', 'sma', 'rsi']);
  });

  it('keeps the catalog order without favorites', () => {
    expect(orderByFavorites(catalog, []).map((item) => item.key)).toEqual(['sma', 'ema', 'rsi', 'macd']);
  });
});
