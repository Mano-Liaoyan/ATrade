// Calls GET /api/market-data/instrument-search and turns the answer into results or a message for the search panel.
import { describe, expect, it } from 'vite-plus/test';
import { formatInstrument, searchInstruments } from './index';

function respondWith(status: number, body: unknown): typeof fetch {
  return () => Promise.resolve(new Response(JSON.stringify(body), { status }));
}

describe('searchInstruments', () => {
  it('returns the instruments that the backend finds', async () => {
    const fetchSearch = respondWith(200, { instruments: [{ symbol: '700', exchange: 'SEHK', currency: 'HKD' }] });

    const searchResult = await searchInstruments(fetchSearch, '700');

    expect(searchResult).toEqual({ kind: 'found', instruments: [{ symbol: '700', exchange: 'SEHK', currency: 'HKD' }] });
  });

  it('sends the query in the URL', async () => {
    const requestedUrls: string[] = [];
    const recordingFetch: typeof fetch = (input) => {
      if (typeof input === 'string') {
        requestedUrls.push(input);
      }
      return Promise.resolve(new Response(JSON.stringify({ instruments: [] }), { status: 200 }));
    };

    await searchInstruments(recordingFetch, 'BRK B');

    expect(requestedUrls).toEqual(['/api/market-data/instrument-search?query=BRK+B']);
  });

  it('shows the backend message when IB Gateway is not reachable', async () => {
    const fetchSearch = respondWith(503, {
      detail: 'IB Gateway is not reachable at ib-gateway:4004. Instrument search needs IB Gateway.',
    });

    const searchResult = await searchInstruments(fetchSearch, '700');

    expect(searchResult).toEqual({
      kind: 'failed',
      message: 'IB Gateway is not reachable at ib-gateway:4004. Instrument search needs IB Gateway.',
    });
  });

  it('shows the backend message when IB Gateway answers with an error', async () => {
    const fetchSearch = respondWith(502, { detail: 'The instrument search failed: timeout.' });

    const searchResult = await searchInstruments(fetchSearch, '700');

    expect(searchResult).toEqual({ kind: 'failed', message: 'The instrument search failed: timeout.' });
  });

  it('says that the backend is not reachable when the request fails', async () => {
    const failingFetch: typeof fetch = () => Promise.reject(new TypeError('Failed to fetch'));

    const searchResult = await searchInstruments(failingFetch, '700');

    expect(searchResult).toEqual({ kind: 'failed', message: 'Backend not reachable. The instrument search did not run.' });
  });

  it('names the HTTP status when a proxy answers without a message', async () => {
    const searchResult = await searchInstruments(respondWith(504, 'Gateway Timeout'), '700');

    expect(searchResult).toEqual({ kind: 'failed', message: 'The instrument search failed with HTTP status 504.' });
  });
});

describe('formatInstrument', () => {
  it('writes symbol, exchange, and currency', () => {
    expect(formatInstrument({ symbol: '700', exchange: 'SEHK', currency: 'HKD' })).toBe('700 / SEHK / HKD');
  });
});
