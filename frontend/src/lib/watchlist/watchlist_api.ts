// Calls the watchlist HTTP routes (backend/src/atrade/watchlist/http_routes.py).
import type { components } from '#lib/api';
import { jsonRequest, requestJson, sendCommand, type RequestResult } from '#lib/foundation/http_request';

export type WatchlistInstrument = components['schemas']['WatchlistInstrumentResponse'];
export type InstrumentToAdd = components['schemas']['AddInstrumentRequest'];
type WatchlistResponse = components['schemas']['WatchlistResponse'];

export type { RequestResult } from '#lib/foundation/http_request';

// The change socket of the list: a "changed" message after each change (foundation/live_socket readOnChange).
export const WATCHLIST_SOCKET_PATH = '/ws/watchlist';
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
  return requestJson<WatchlistInstrument>(fetchFunction, FAILED_ACTION, WATCHLIST_PATH, jsonRequest('POST', body));
}

export function deleteFromWatchlist(
  fetchFunction: typeof fetch,
  watchlistInstrumentId: number,
): Promise<RequestResult<undefined>> {
  return sendCommand(fetchFunction, FAILED_ACTION, `${WATCHLIST_PATH}/${String(watchlistInstrumentId)}`, { method: 'DELETE' });
}

export function formatWatchlistInstrument(instrument: InstrumentToAdd): string {
  return `${instrument.symbol} / ${instrument.exchange} / ${instrument.currency}`;
}
