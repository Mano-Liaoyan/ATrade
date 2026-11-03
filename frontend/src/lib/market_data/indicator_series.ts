// Calls GET /api/market-data/indicators and POST /api/market-data/indicator-series (indicator.md section 23.9.6).
// The series route reads only saved bars, so the chart asks for it after the bars route answered.
import type { components } from '#lib/api';
import { BACKEND_NOT_REACHABLE, readErrorMessage, readJsonBody, requestJson, sendRequest, type RequestResult } from '#lib/foundation/http_request';
import type { BarPeriod } from './bars';
import type { ChartIndicatorDefinition, ChartPane } from './chart_indicators';
import type { Instrument } from './instrument_search';
import type { BarSource } from './source_order';

export type IndicatorSeriesResult = components['schemas']['IndicatorSeriesResponse'];
type IndicatorProblem = components['schemas']['IndicatorProblemResponse'];

const FAILED_ACTION = 'Reading the indicator values';

/** The indicator catalog in its own order, with the short name and the chart placement. */
export function listChartIndicatorCatalog(fetchFunction: typeof fetch): Promise<RequestResult<ChartIndicatorDefinition[]>> {
  return requestJson(fetchFunction, 'Reading the indicator list', '/api/market-data/indicators');
}

export interface IndicatorSeriesRequest {
  instrument: Instrument;
  barPeriod: BarPeriod;
  /** The start (UNIX seconds) of the first and of the last bar of the chart. */
  firstBarTime: number;
  lastBarTime: number;
  sourceOrder?: BarSource[];
  indicators: { indicator: string; parameters: Record<string, number> }[];
}

/** All indicators of the panes, in pane order. The series answer has one series for each, in the same order. */
export function listSeriesIndicators(panes: readonly ChartPane[]): IndicatorSeriesRequest['indicators'] {
  return panes.flatMap((pane) => pane.indicators.map(({ indicator, parameters }) => ({ indicator, parameters })));
}

const MILLISECONDS_PER_SECOND = 1000;

function toIsoTime(unixSeconds: number): string {
  return new Date(unixSeconds * MILLISECONDS_PER_SECOND).toISOString();
}

export async function readIndicatorSeries(
  fetchFunction: typeof fetch,
  request: IndicatorSeriesRequest,
): Promise<RequestResult<IndicatorSeriesResult>> {
  const { symbol, exchange, currency } = request.instrument;
  const body = {
    symbol,
    exchange,
    currency,
    bar_period: request.barPeriod,
    start_utc: toIsoTime(request.firstBarTime),
    // The end is not included: 1 second after the start of the last bar includes the last bar.
    end_utc: toIsoTime(request.lastBarTime + 1),
    ...(request.sourceOrder === undefined ? {} : { source_order: request.sourceOrder }),
    indicators: request.indicators,
  };
  const response = await sendRequest(fetchFunction, '/api/market-data/indicator-series', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (response === null) {
    return { kind: 'failed', message: BACKEND_NOT_REACHABLE };
  }
  if (!response.ok) {
    const problems = ((await readJsonBody(response.clone())) as { problems?: IndicatorProblem[] } | null)?.problems;
    const firstProblem = Array.isArray(problems) ? problems[0] : undefined;
    return { kind: 'failed', message: firstProblem?.message ?? (await readErrorMessage(response, FAILED_ACTION)) };
  }
  return { kind: 'ok', value: (await response.json()) as IndicatorSeriesResult };
}
