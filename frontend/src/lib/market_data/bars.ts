// Calls GET /api/market-data/bars. The backend picks the default range of the bar period, up to now.
// The instrument page URL names the instrument and the bar period, so a chart link can be opened again.
import type { components } from '#lib/api';
import { readErrorMessage } from './http_errors';
import type { Instrument } from './instrument_search';

export type Bar = components['schemas']['BarResponse'];
export type BarPeriod = components['schemas']['BarPeriod'];
type BarsResponse = components['schemas']['BarsResponse'];

export type BarsResult = { kind: 'loaded'; bars: Bar[] } | { kind: 'failed'; message: string };
export type ChartRequest = { instrument: Instrument; barPeriod: BarPeriod };

export const BAR_PERIODS: readonly { value: BarPeriod; label: string }[] = [
  { value: '1-MINUTE', label: '1 minute' },
  { value: '5-MINUTE', label: '5 minutes' },
  { value: '15-MINUTE', label: '15 minutes' },
  { value: '30-MINUTE', label: '30 minutes' },
  { value: '1-HOUR', label: '1 hour' },
  { value: '1-DAY', label: '1 day' },
];
export const DEFAULT_BAR_PERIOD: BarPeriod = '1-DAY';

const BARS_PATH = '/api/market-data/bars';

export async function readBars(
  fetchFunction: typeof fetch,
  instrument: Instrument,
  barPeriod: BarPeriod,
): Promise<BarsResult> {
  let response: Response;
  try {
    const { symbol, exchange, currency } = instrument;
    const searchParameters = new URLSearchParams({ symbol, exchange, currency, bar_period: barPeriod });
    response = await fetchFunction(`${BARS_PATH}?${searchParameters.toString()}`);
  } catch {
    return { kind: 'failed', message: 'Backend not reachable. The bars did not load.' };
  }
  if (!response.ok) {
    return { kind: 'failed', message: await readErrorMessage(response, 'Reading the bars') };
  }
  const barsResponse = (await response.json()) as BarsResponse;
  return { kind: 'loaded', bars: barsResponse.bars };
}

export function formatChartSearch(chartRequest: ChartRequest): string {
  return new URLSearchParams({
    currency: chartRequest.instrument.currency,
    bar_period: chartRequest.barPeriod,
  }).toString();
}

// The instrument page is /instruments/<exchange>/<symbol>?currency=<currency>&bar_period=<bar period>.
export function readChartRequest(
  routeParameters: { exchange?: string; symbol?: string },
  searchParameters: Pick<URLSearchParams, 'get'>,
): ChartRequest | null {
  const { exchange, symbol } = routeParameters;
  const currency = searchParameters.get('currency');
  if (exchange === undefined || symbol === undefined || currency === null || currency === '') {
    return null;
  }
  const requestedPeriod = searchParameters.get('bar_period');
  const knownPeriod = BAR_PERIODS.find((barPeriod) => barPeriod.value === requestedPeriod);
  return { instrument: { symbol, exchange, currency }, barPeriod: knownPeriod?.value ?? DEFAULT_BAR_PERIOD };
}
