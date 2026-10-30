// Calls the HK instrument list routes (backend/src/atrade/market_data/hk_instrument_list_routes.py).
import type { components } from '#lib/api';
import {
  BACKEND_NOT_REACHABLE,
  readErrorMessage,
  requestJson,
  sendRequest,
  type RequestResult,
} from '#lib/foundation/http_request';

export type HkInstrument = components['schemas']['HkInstrumentResponse'];
export type HkInstrumentsAdded = components['schemas']['AddHkInstrumentsResponse'];
type HkInstrumentListResponse = components['schemas']['HkInstrumentListResponse'];

const HK_INSTRUMENT_LIST_PATH = '/api/market-data/hk-instrument-list';
// The backend sends {"detail": "<message>"} for 404, 502, and 503. A proxy sends no JSON.
const FAILED_ACTION = 'The HK instrument list request';

// The user pastes symbols from a list or a spreadsheet: spaces, tabs, commas, and line ends separate them.
export function splitPastedSymbols(text: string): string[] {
  return text.split(/[\s,]+/u).filter((symbol) => symbol !== '');
}

export async function listHkInstrumentList(fetchFunction: typeof fetch): Promise<RequestResult<HkInstrument[]>> {
  const result = await requestJson<HkInstrumentListResponse>(fetchFunction, FAILED_ACTION, HK_INSTRUMENT_LIST_PATH);
  if (result.kind === 'failed') {
    return result;
  }
  return { kind: 'ok', value: result.value.instruments };
}

export function addToHkInstrumentList(
  fetchFunction: typeof fetch,
  symbols: string[],
): Promise<RequestResult<HkInstrumentsAdded>> {
  return requestJson<HkInstrumentsAdded>(fetchFunction, FAILED_ACTION, HK_INSTRUMENT_LIST_PATH, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ symbols }),
  });
}

export async function deleteFromHkInstrumentList(
  fetchFunction: typeof fetch,
  hkInstrumentId: number,
): Promise<RequestResult<undefined>> {
  const response = await sendRequest(fetchFunction, `${HK_INSTRUMENT_LIST_PATH}/${String(hkInstrumentId)}`, {
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
