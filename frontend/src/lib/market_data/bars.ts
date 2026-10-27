// Calls GET /api/market-data/bars. The backend picks the default range of the bar period, up to now.
// The chart page URL names the instrument and the bar period, so a chart link can be opened again.
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
    response = await fetchFunction(`${BARS_PATH}?${formatChartQuery({ instrument, barPeriod })}`);
  } catch {
    return { kind: 'failed', message: 'Backend not reachable. The bars did not load.' };
  }
  if (!response.ok) {
    return { kind: 'failed', message: await readErrorMessage(response, 'Reading the bars') };
  }
  const barsResponse = (await response.json()) as BarsResponse;
  return { kind: 'loaded', bars: barsResponse.bars };
}

// The chart page URL and the bars route use the same query parameters.
export function formatChartQuery(chartRequest: ChartRequest): string {
  const { instrument, barPeriod } = chartRequest;
  return new URLSearchParams({
    symbol: instrument.symbol,
    exchange: instrument.exchange,
    currency: instrument.currency,
    bar_period: barPeriod,
  }).toString();
}

export function readChartRequest(searchParameters: URLSearchParams): ChartRequest | null {
  const symbol = searchParameters.get('symbol');
  const exchange = searchParameters.get('exchange');
  const currency = searchParameters.get('currency');
  if (symbol === null || exchange === null || currency === null || symbol === '' || exchange === '' || currency === '') {
    return null;
  }
  const requestedPeriod = searchParameters.get('bar_period');
  const knownPeriod = BAR_PERIODS.find((barPeriod) => barPeriod.value === requestedPeriod);
  return { instrument: { symbol, exchange, currency }, barPeriod: knownPeriod?.value ?? DEFAULT_BAR_PERIOD };
}
