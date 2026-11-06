// Calls the HK instrument list routes (backend/src/atrade/market_data/hk_instrument_list_routes.py).
import type { components } from '#lib/api';
import { jsonRequest, requestJson, sendCommand, type RequestResult } from '#lib/foundation/http_request';

export type HkInstrument = components['schemas']['HkInstrumentResponse'];
export type HkInstrumentsAdded = components['schemas']['AddHkInstrumentsResponse'];
type HkInstrumentListResponse = components['schemas']['HkInstrumentListResponse'];

const HK_INSTRUMENT_LIST_PATH = '/api/market-data/hk-instrument-list';
// The start of the error message when the response has no {"detail": "<message>"}, for example from a proxy.
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
  return requestJson<HkInstrumentsAdded>(fetchFunction, FAILED_ACTION, HK_INSTRUMENT_LIST_PATH, jsonRequest('POST', { symbols }));
}

export function deleteFromHkInstrumentList(
  fetchFunction: typeof fetch,
  hkInstrumentId: number,
): Promise<RequestResult<undefined>> {
  return sendCommand(fetchFunction, FAILED_ACTION, `${HK_INSTRUMENT_LIST_PATH}/${String(hkInstrumentId)}`, { method: 'DELETE' });
}
