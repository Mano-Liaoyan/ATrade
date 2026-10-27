// Calls the watchlist HTTP routes (backend/src/atrade/watchlist/http_routes.py).
import type { components } from '#lib/api';

export type WatchlistInstrument = components['schemas']['WatchlistInstrumentResponse'];
export type InstrumentToAdd = components['schemas']['AddInstrumentRequest'];
type WatchlistResponse = components['schemas']['WatchlistResponse'];

export type RequestResult<T> = { kind: 'ok'; value: T } | { kind: 'failed'; message: string };

const WATCHLIST_PATH = '/api/watchlist';
const BACKEND_NOT_REACHABLE = 'The backend is not reachable.';

// The backend sends {"detail": "<message>"} for 404, 409, 502, and 503. A proxy sends no JSON.
async function readFailureMessage(response: Response): Promise<string> {
  const statusMessage = `The watchlist request failed with HTTP status ${String(response.status)}.`;
  let errorBody: unknown;
  try {
    errorBody = await response.json();
  } catch {
    return statusMessage;
  }
  if (typeof errorBody === 'object' && errorBody !== null && 'detail' in errorBody && typeof errorBody.detail === 'string') {
    return errorBody.detail;
  }
  return statusMessage;
}

async function sendRequest(
  fetchFunction: typeof fetch,
  path: string,
  init?: RequestInit,
): Promise<RequestResult<Response>> {
  let response: Response;
  try {
    response = await fetchFunction(path, init);
  } catch {
    return { kind: 'failed', message: BACKEND_NOT_REACHABLE };
  }
  if (!response.ok) {
    return { kind: 'failed', message: await readFailureMessage(response) };
  }
  return { kind: 'ok', value: response };
}

export async function listWatchlist(fetchFunction: typeof fetch): Promise<RequestResult<WatchlistInstrument[]>> {
  const result = await sendRequest(fetchFunction, WATCHLIST_PATH);
  if (result.kind === 'failed') {
    return result;
  }
  const watchlist = (await result.value.json()) as WatchlistResponse;
  return { kind: 'ok', value: watchlist.instruments };
}

export async function addToWatchlist(
  fetchFunction: typeof fetch,
  instrument: InstrumentToAdd,
): Promise<RequestResult<WatchlistInstrument>> {
  const body = { symbol: instrument.symbol, exchange: instrument.exchange, currency: instrument.currency };
  const result = await sendRequest(fetchFunction, WATCHLIST_PATH, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (result.kind === 'failed') {
    return result;
  }
  return { kind: 'ok', value: (await result.value.json()) as WatchlistInstrument };
}

export async function deleteFromWatchlist(
  fetchFunction: typeof fetch,
  watchlistInstrumentId: number,
): Promise<RequestResult<undefined>> {
  const result = await sendRequest(fetchFunction, `${WATCHLIST_PATH}/${String(watchlistInstrumentId)}`, {
    method: 'DELETE',
  });
  if (result.kind === 'failed') {
    return result;
  }
  return { kind: 'ok', value: undefined };
}

export function formatWatchlistInstrument(instrument: InstrumentToAdd): string {
  return `${instrument.symbol} / ${instrument.exchange} / ${instrument.currency}`;
}
