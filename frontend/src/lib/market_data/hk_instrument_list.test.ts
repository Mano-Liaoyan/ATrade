// Calls the HK instrument list routes and splits pasted text into symbols.
import { describe, expect, it } from 'vite-plus/test';
import { addToHkInstrumentList, deleteFromHkInstrumentList, listHkInstrumentList, splitPastedSymbols } from './index';

const TENCENT = { id: 7, symbol: '700', exchange: 'SEHK', currency: 'HKD', added_at_utc: '2026-01-02T03:04:05Z' };

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

describe('splitPastedSymbols', () => {
  it('splits at spaces, commas, and line ends and drops empty parts', () => {
    expect(splitPastedSymbols(' 700, 9988\n5\t\t1299,,')).toEqual(['700', '9988', '5', '1299']);
  });

  it('gives no symbols for empty text', () => {
    expect(splitPastedSymbols(' \n ')).toEqual([]);
  });
});

describe('listHkInstrumentList', () => {
  it('returns the instruments of the list', async () => {
    const { fetchFunction, requests } = recordRequests(200, { instruments: [TENCENT] });

    const listResult = await listHkInstrumentList(fetchFunction);

    expect(listResult).toEqual({ kind: 'ok', value: [TENCENT] });
    expect(requests).toEqual([{ url: '/api/market-data/hk-instrument-list', method: 'GET', body: null }]);
  });
});

describe('addToHkInstrumentList', () => {
  it('sends the symbols and returns the result of each symbol', async () => {
    const addResponse = { added: ['700'], not_found: ['1'], already_in_list: ['9988'] };
    const { fetchFunction, requests } = recordRequests(200, addResponse);

    const addResult = await addToHkInstrumentList(fetchFunction, ['700', '1', '9988']);

    expect(addResult).toEqual({ kind: 'ok', value: addResponse });
    expect(requests).toEqual([
      { url: '/api/market-data/hk-instrument-list', method: 'POST', body: '{"symbols":["700","1","9988"]}' },
    ]);
  });

  it('returns the detail of the backend when IB Gateway is not reachable', async () => {
    const detail = 'IB Gateway is not reachable at ib-gateway:4004. The instrument check needs IB Gateway.';
    const { fetchFunction } = recordRequests(503, { detail });

    const addResult = await addToHkInstrumentList(fetchFunction, ['700']);

    expect(addResult).toEqual({ kind: 'failed', message: detail });
  });
});

describe('deleteFromHkInstrumentList', () => {
  it('deletes the instrument by its ID', async () => {
    const { fetchFunction, requests } = recordRequests(204, null);

    const deleteResult = await deleteFromHkInstrumentList(fetchFunction, 7);

    expect(deleteResult).toEqual({ kind: 'ok', value: undefined });
    expect(requests).toEqual([{ url: '/api/market-data/hk-instrument-list/7', method: 'DELETE', body: null }]);
  });

  it('returns the detail of the backend when the instrument is not in the list', async () => {
    const detail = 'This instrument is not in the HK instrument list.';
    const { fetchFunction } = recordRequests(404, { detail });

    const deleteResult = await deleteFromHkInstrumentList(fetchFunction, 7);

    expect(deleteResult).toEqual({ kind: 'failed', message: detail });
  });
});
