// Calls GET /api/market-data/instrument-search. Turns the answer into results, or into a message for the user.
import type { components } from '#lib/api';
import { readErrorMessage } from './http_errors';

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
    return { kind: 'failed', message: await readErrorMessage(response, 'The instrument search') };
  }
  const searchResponse = (await response.json()) as InstrumentSearchResponse;
  return { kind: 'found', instruments: searchResponse.instruments };
}

export function formatInstrument(instrument: Instrument): string {
  return `${instrument.symbol} / ${instrument.exchange} / ${instrument.currency}`;
}
