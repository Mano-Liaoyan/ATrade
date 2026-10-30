// The source order choices of the backtest form, and the read, the save, and a move in the global source order.
import { describe, expect, it } from 'vite-plus/test';
import {
  formatBarSource,
  formatSourceOrder,
  listSourceOrders,
  moveBarSource,
  readSourceOrder,
  saveSourceOrder,
} from './source_order';

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

describe('listSourceOrders', () => {
  it('gives each order of the bar sources once, the given order first', () => {
    expect(listSourceOrders(['databento', 'ibkr'])).toEqual([
      ['databento', 'ibkr'],
      ['ibkr', 'databento'],
    ]);
  });
});

describe('formatSourceOrder', () => {
  it('names the bar sources in their order', () => {
    expect(formatSourceOrder(['ibkr', 'databento'])).toBe('IBKR, Databento');
    expect(formatBarSource('databento')).toBe('Databento');
  });
});

describe('readSourceOrder', () => {
  it('returns the global source order', async () => {
    const answeringFetch: typeof fetch = () =>
      Promise.resolve(new Response(JSON.stringify({ source_order: ['databento', 'ibkr'] }), { status: 200 }));

    expect(await readSourceOrder(answeringFetch)).toEqual({ kind: 'ok', value: ['databento', 'ibkr'] });
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
