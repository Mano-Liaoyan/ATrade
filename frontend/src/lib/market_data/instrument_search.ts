// Calls GET /api/market-data/instrument-search. Turns the answer into results, or into a message for the user.
import type { components } from '#lib/api';
import { readErrorMessage, sendRequest } from '#lib/foundation/http_request';

export type Instrument = components['schemas']['InstrumentResponse'];
type InstrumentSearchResponse = components['schemas']['InstrumentSearchResponse'];

export type InstrumentSearchResult = { kind: 'found'; instruments: Instrument[] } | { kind: 'failed'; message: string };

const INSTRUMENT_SEARCH_PATH = '/api/market-data/instrument-search';

export async function searchInstruments(fetchFunction: typeof fetch, query: string): Promise<InstrumentSearchResult> {
  const searchParameters = new URLSearchParams({ query });
  const response = await sendRequest(fetchFunction, `${INSTRUMENT_SEARCH_PATH}?${searchParameters.toString()}`);
  if (response === null) {
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

/** The symbol, the exchange, and the currency identify an instrument (GLOSSARY.md). */
export function isSameInstrument(first: Instrument, second: Instrument): boolean {
  return formatInstrument(first) === formatInstrument(second);
}
