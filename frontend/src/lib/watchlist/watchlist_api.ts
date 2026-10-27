// Calls the watchlist HTTP routes (backend/src/atrade/watchlist/http_routes.py).
import type { components } from '#lib/api';
import {
  BACKEND_NOT_REACHABLE,
  readErrorMessage,
  requestJson,
  sendRequest,
  type RequestResult,
} from '#lib/foundation/http_request';

export type WatchlistInstrument = components['schemas']['WatchlistInstrumentResponse'];
export type InstrumentToAdd = components['schemas']['AddInstrumentRequest'];
type WatchlistResponse = components['schemas']['WatchlistResponse'];

export type { RequestResult } from '#lib/foundation/http_request';

const WATCHLIST_PATH = '/api/watchlist';
// The backend sends {"detail": "<message>"} for 404, 409, 502, and 503. A proxy sends no JSON.
const FAILED_ACTION = 'The watchlist request';

export async function listWatchlist(fetchFunction: typeof fetch): Promise<RequestResult<WatchlistInstrument[]>> {
  const result = await requestJson<WatchlistResponse>(fetchFunction, FAILED_ACTION, WATCHLIST_PATH);
  if (result.kind === 'failed') {
    return result;
  }
  return { kind: 'ok', value: result.value.instruments };
}

export function addToWatchlist(
  fetchFunction: typeof fetch,
  instrument: InstrumentToAdd,
): Promise<RequestResult<WatchlistInstrument>> {
  const body = { symbol: instrument.symbol, exchange: instrument.exchange, currency: instrument.currency };
  return requestJson<WatchlistInstrument>(fetchFunction, FAILED_ACTION, WATCHLIST_PATH, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
}

export async function deleteFromWatchlist(
  fetchFunction: typeof fetch,
  watchlistInstrumentId: number,
): Promise<RequestResult<undefined>> {
  const response = await sendRequest(fetchFunction, `${WATCHLIST_PATH}/${String(watchlistInstrumentId)}`, {
    method: 'DELETE',
  });
  if (response === null) {
    return { kind: 'failed', message: BACKEND_NOT_REACHABLE };
  }
  if (!response.ok) {
    return { kind: 'failed', message: await readErrorMessage(response, FAILED_ACTION) };
  }
  return { kind: 'ok', value: undefined };
}

export function formatWatchlistInstrument(instrument: InstrumentToAdd): string {
  return `${instrument.symbol} / ${instrument.exchange} / ${instrument.currency}`;
}
