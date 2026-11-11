// Calls the backtest HTTP routes (backend/src/atrade/backtest/http_routes.py).

import type { components } from '#lib/api';
import { jsonRequest, requestJson, sendCommand, type RequestResult } from '#lib/foundation/http_request';

// The generated type makes the fields with a default required. Without `out_of_sample_share`, the route uses 30.
export type BacktestRequest = Omit<components['schemas']['StartBacktestRequest'], 'out_of_sample_share'> & {
  out_of_sample_share?: number;
};
export type Backtest = components['schemas']['BacktestResponse'];
export type BacktestDetail = components['schemas']['BacktestDetailResponse'];
export type BacktestStatus = components['schemas']['BacktestStatus'];
export type BacktestMetrics = components['schemas']['BacktestMetricsResponse'];
export type EquityPoint = components['schemas']['EquityPointResponse'];
export type BacktestTrade = components['schemas']['TradeResponse'];
export type BacktestLimits = components['schemas']['BacktestLimitsBody'];
export type BacktestComparison = components['schemas']['BacktestComparisonResponse'];
export type UniverseInstrument = components['schemas']['UniverseInstrumentResponse'];
export type UsUniverseRange = components['schemas']['UsUniverseRangeResponse'];

export type { RequestResult } from '#lib/foundation/http_request';

export interface BacktestInstrument {
  symbol: string;
  exchange: string;
  currency: string;
}

// The instrument of a single-instrument backtest. A multi-instrument backtest has none.
export function readBacktestInstrument(backtest: Backtest): BacktestInstrument | undefined {
  const { symbol, exchange, currency } = backtest;
  if (symbol === null || exchange === null || currency === null) {
    return undefined;
  }
  return { symbol, exchange, currency };
}

// The instruments that the "Bars" view can show: the instrument of a single-instrument backtest, or the universe
// members with currency, the members with trades first. A backtest from before the migration has no currency: none.
export function listChartInstruments(backtest: BacktestDetail): BacktestInstrument[] {
  const instrument = readBacktestInstrument(backtest);
  if (instrument !== undefined) {
    return [instrument];
  }
  const { currency, instruments } = backtest;
  if (currency === null) {
    return [];
  }
  return [...instruments]
    .sort((first, second) => Number(second.trade_count > 0) - Number(first.trade_count > 0))
    .map(({ symbol, exchange }) => ({ symbol, exchange, currency }));
}

// The change socket of the list: a "changed" message after each change (foundation/live_socket readOnChange).
export const BACKTESTS_SOCKET_PATH = '/ws/backtests';
const BACKTESTS_PATH = '/api/backtests';
const BACKTEST_LIMITS_PATH = '/api/backtest-limits';
// A refused request has ErrorResponse {"detail": "<reason>"}. A request that does not validate has HTTPValidationError.
const FAILED_ACTION = 'The backtest request';

export function startBacktest(fetchFunction: typeof fetch, request: BacktestRequest): Promise<RequestResult<Backtest>> {
  return requestJson(fetchFunction, FAILED_ACTION, BACKTESTS_PATH, jsonRequest('POST', request));
}

/** A new backtest of the strategy version on the data of the backtest: the same instruments, universe members, bar
 * period, range, paper capital, out-of-sample share, and source order. The version must be of the same strategy. */
export function rerunBacktest(
  fetchFunction: typeof fetch,
  backtestId: number,
  strategyVersionId: number,
): Promise<RequestResult<Backtest>> {
  return requestJson(
    fetchFunction,
    FAILED_ACTION,
    `${BACKTESTS_PATH}/${String(backtestId)}/rerun`,
    jsonRequest('POST', { strategy_version_id: strategyVersionId }),
  );
}

export function listBacktests(fetchFunction: typeof fetch): Promise<RequestResult<Backtest[]>> {
  return requestJson(fetchFunction, FAILED_ACTION, BACKTESTS_PATH);
}

export type DeleteBacktestResult = { kind: 'deleted' } | { kind: 'failed'; message: string };

/** A true delete. The backend refuses a queued or running backtest, a sweep run, and the same-period backtest of a
 * forward test (409 with the reason). */
export async function deleteBacktest(fetchFunction: typeof fetch, backtestId: number): Promise<DeleteBacktestResult> {
  const result = await sendCommand(fetchFunction, FAILED_ACTION, `${BACKTESTS_PATH}/${String(backtestId)}`, { method: 'DELETE' });
  return result.kind === 'failed' ? result : { kind: 'deleted' };
}

export function readBacktest(fetchFunction: typeof fetch, backtestId: number): Promise<RequestResult<BacktestDetail>> {
  return requestJson(fetchFunction, FAILED_ACTION, `${BACKTESTS_PATH}/${String(backtestId)}`);
}

export function readBacktestLimits(fetchFunction: typeof fetch): Promise<RequestResult<BacktestLimits>> {
  return requestJson(fetchFunction, FAILED_ACTION, BACKTEST_LIMITS_PATH);
}

export function changeBacktestLimits(
  fetchFunction: typeof fetch,
  limits: BacktestLimits,
): Promise<RequestResult<BacktestLimits>> {
  return requestJson(fetchFunction, FAILED_ACTION, BACKTEST_LIMITS_PATH, jsonRequest('PUT', limits));
}

export function compareBacktests(
  fetchFunction: typeof fetch,
  firstBacktestId: number,
  secondBacktestId: number,
): Promise<RequestResult<BacktestComparison>> {
  return requestJson(fetchFunction, FAILED_ACTION, `${BACKTESTS_PATH}/${String(firstBacktestId)}/comparison/${String(secondBacktestId)}`);
}

// The first and the last quarter start with US universe data (docs/architecture/backtest.md 10.10.6).
export function readUsUniverseRange(fetchFunction: typeof fetch): Promise<RequestResult<UsUniverseRange>> {
  return requestJson(fetchFunction, FAILED_ACTION, '/api/us-universe/range');
}
