// Reads and saves the global source order, and moves one bar source up or down in it.
import { describe, expect, it } from 'vite-plus/test';
import { formatBarSource, moveBarSource, readSourceOrder, saveSourceOrder } from './index';

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

describe('readSourceOrder', () => {
  it('returns the bar sources in the source order', async () => {
    const { fetchFunction, requests } = recordRequests(200, { source_order: ['databento', 'ibkr'] });

    const readResult = await readSourceOrder(fetchFunction);

    expect(readResult).toEqual({ kind: 'ok', value: ['databento', 'ibkr'] });
    expect(requests).toEqual([{ url: '/api/market-data/source-order', method: 'GET', body: null }]);
  });
});

describe('saveSourceOrder', () => {
  it('sends the new source order with PUT', async () => {
    const { fetchFunction, requests } = recordRequests(200, { source_order: ['databento', 'ibkr'] });

    const saveResult = await saveSourceOrder(fetchFunction, ['databento', 'ibkr']);

    expect(saveResult).toEqual({ kind: 'ok', value: ['databento', 'ibkr'] });
    expect(requests).toEqual([
      { url: '/api/market-data/source-order', method: 'PUT', body: '{"source_order":["databento","ibkr"]}' },
    ]);
  });

  it('gives the detail text of the backend when the backend refuses the order', async () => {
    const { fetchFunction } = recordRequests(422, { detail: 'The source order has a bar source 2 times.' });

    const saveResult = await saveSourceOrder(fetchFunction, ['ibkr', 'ibkr']);

    expect(saveResult).toEqual({ kind: 'failed', message: 'The source order has a bar source 2 times.' });
  });
});

describe('moveBarSource', () => {
  it('moves a bar source up by one place', () => {
    expect(moveBarSource(['ibkr', 'databento'], 1, 'up')).toEqual(['databento', 'ibkr']);
  });

  it('moves a bar source down by one place', () => {
    expect(moveBarSource(['ibkr', 'databento'], 0, 'down')).toEqual(['databento', 'ibkr']);
  });
});

describe('formatBarSource', () => {
  it('names each bar source as the glossary does', () => {
    expect(formatBarSource('ibkr')).toBe('IBKR');
    expect(formatBarSource('databento')).toBe('Databento');
  });
});
