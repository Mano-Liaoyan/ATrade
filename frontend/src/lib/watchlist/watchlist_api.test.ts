// Calls the watchlist routes and turns each answer into a value, or into a message for the watchlist column.
import { describe, expect, it } from 'vite-plus/test';
import { addToWatchlist, deleteFromWatchlist, listWatchlist } from './index';

const TENCENT = { id: 7, symbol: '700', exchange: 'SEHK', currency: 'HKD', added_at_utc: '2026-01-02T03:04:05Z', saved_bars: [] };

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
    const responseBody = status === 204 ? null : JSON.stringify(body);
    return Promise.resolve(new Response(responseBody, { status }));
  };
  return { fetchFunction, requests };
}

describe('listWatchlist', () => {
  it('returns the watchlist instruments', async () => {
    const { fetchFunction, requests } = recordRequests(200, { instruments: [TENCENT] });

    const listResult = await listWatchlist(fetchFunction);

    expect(listResult).toEqual({ kind: 'ok', value: [TENCENT] });
    expect(requests).toEqual([{ url: '/api/watchlist', method: 'GET', body: null }]);
  });

  it('says that the backend is not reachable when the request fails', async () => {
    const failingFetch: typeof fetch = () => Promise.reject(new TypeError('Failed to fetch'));

    const listResult = await listWatchlist(failingFetch);

    expect(listResult).toEqual({ kind: 'failed', message: 'The backend is not reachable.' });
  });
});

describe('addToWatchlist', () => {
  it('sends symbol, exchange, and currency', async () => {
    const { fetchFunction, requests } = recordRequests(201, TENCENT);

    const addResult = await addToWatchlist(fetchFunction, { symbol: '700', exchange: 'SEHK', currency: 'HKD' });

    expect(addResult).toEqual({ kind: 'ok', value: TENCENT });
    expect(requests).toEqual([
      { url: '/api/watchlist', method: 'POST', body: '{"symbol":"700","exchange":"SEHK","currency":"HKD"}' },
    ]);
  });

  it('shows the backend message when the instrument is already in the watchlist', async () => {
    const { fetchFunction } = recordRequests(409, { detail: 'This instrument is already in the watchlist.' });

    const addResult = await addToWatchlist(fetchFunction, { symbol: '700', exchange: 'SEHK', currency: 'HKD' });

    expect(addResult).toEqual({ kind: 'failed', message: 'This instrument is already in the watchlist.' });
  });

  it('names the HTTP status when a proxy answers without a message', async () => {
    const fetchFunction: typeof fetch = () => Promise.resolve(new Response('Bad Gateway', { status: 502 }));

    const addResult = await addToWatchlist(fetchFunction, { symbol: '700', exchange: 'SEHK', currency: 'HKD' });

    expect(addResult).toEqual({ kind: 'failed', message: 'The watchlist request failed with HTTP status 502.' });
  });
});

describe('deleteFromWatchlist', () => {
  it('deletes the watchlist instrument by its ID', async () => {
    const { fetchFunction, requests } = recordRequests(204, null);

    const deleteResult = await deleteFromWatchlist(fetchFunction, 7);

    expect(deleteResult).toEqual({ kind: 'ok', value: undefined });
    expect(requests).toEqual([{ url: '/api/watchlist/7', method: 'DELETE', body: null }]);
  });

  it('shows the backend message when the instrument is not in the watchlist', async () => {
    const { fetchFunction } = recordRequests(404, { detail: 'This instrument is not in the watchlist.' });

    const deleteResult = await deleteFromWatchlist(fetchFunction, 7);

    expect(deleteResult).toEqual({ kind: 'failed', message: 'This instrument is not in the watchlist.' });
  });
});
