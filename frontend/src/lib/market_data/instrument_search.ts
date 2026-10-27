// Calls GET /api/market-data/instrument-search. Turns the answer into results, or into a message for the user.
import type { components } from '#lib/api';

export type Instrument = components['schemas']['InstrumentResponse'];
type InstrumentSearchResponse = components['schemas']['InstrumentSearchResponse'];

export type InstrumentSearchResult = { kind: 'found'; instruments: Instrument[] } | { kind: 'failed'; message: string };

const INSTRUMENT_SEARCH_PATH = '/api/market-data/instrument-search';

export async function searchInstruments(fetchFunction: typeof fetch, query: string): Promise<InstrumentSearchResult> {
  const searchParameters = new URLSearchParams({ query });
  let response: Response;
  try {
    response = await fetchFunction(`${INSTRUMENT_SEARCH_PATH}?${searchParameters.toString()}`);
  } catch {
    return { kind: 'failed', message: 'Backend not reachable. The instrument search did not run.' };
  }
  if (!response.ok) {
    return { kind: 'failed', message: await readErrorMessage(response) };
  }
  const searchResponse = (await response.json()) as InstrumentSearchResponse;
  return { kind: 'found', instruments: searchResponse.instruments };
}

// The backend sends {"detail": "<message>"} for 502 and 503. A proxy sends no JSON, and 422 has a list as detail.
async function readErrorMessage(response: Response): Promise<string> {
  const statusMessage = `The instrument search failed with HTTP status ${String(response.status)}.`;
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

export function formatInstrument(instrument: Instrument): string {
  return `${instrument.symbol} / ${instrument.exchange} / ${instrument.currency}`;
}
