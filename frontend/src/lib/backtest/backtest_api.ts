// Calls the backtest HTTP routes (backend/src/atrade/backtest/http_routes.py).

import type { components } from '#lib/api';
import { requestJson as requestBackendJson, type RequestResult } from '#lib/foundation/http_request';

export type BacktestRequest = components['schemas']['StartBacktestRequest'];
export type Backtest = components['schemas']['BacktestResponse'];
export type BacktestDetail = components['schemas']['BacktestDetailResponse'];
export type BacktestStatus = components['schemas']['BacktestStatus'];
export type BacktestMetrics = components['schemas']['BacktestMetricsResponse'];
export type EquityPoint = components['schemas']['EquityPointResponse'];
export type BacktestTrade = components['schemas']['TradeResponse'];
export type BacktestLimits = components['schemas']['BacktestLimitsBody'];
export type BacktestComparison = components['schemas']['BacktestComparisonResponse'];

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

const BACKTESTS_PATH = '/api/backtests';
const BACKTEST_LIMITS_PATH = '/api/backtest-limits';
// A refused request has ErrorResponse {"detail": "<reason>"}. A request that does not validate has HTTPValidationError.
const FAILED_ACTION = 'The backtest request';

function requestJson<T>(fetchFunction: typeof fetch, path: string, init?: RequestInit): Promise<RequestResult<T>> {
  return requestBackendJson<T>(fetchFunction, FAILED_ACTION, path, init);
}

export function startBacktest(fetchFunction: typeof fetch, request: BacktestRequest): Promise<RequestResult<Backtest>> {
  return requestJson(fetchFunction, BACKTESTS_PATH, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(request),
  });
}

export function listBacktests(fetchFunction: typeof fetch): Promise<RequestResult<Backtest[]>> {
  return requestJson(fetchFunction, BACKTESTS_PATH);
}

export function readBacktest(fetchFunction: typeof fetch, backtestId: number): Promise<RequestResult<BacktestDetail>> {
  return requestJson(fetchFunction, `${BACKTESTS_PATH}/${String(backtestId)}`);
}

export function readBacktestLimits(fetchFunction: typeof fetch): Promise<RequestResult<BacktestLimits>> {
  return requestJson(fetchFunction, BACKTEST_LIMITS_PATH);
}

export function changeBacktestLimits(
  fetchFunction: typeof fetch,
  limits: BacktestLimits,
): Promise<RequestResult<BacktestLimits>> {
  return requestJson(fetchFunction, BACKTEST_LIMITS_PATH, {
    method: 'PUT',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(limits),
  });
}

export function compareBacktests(
  fetchFunction: typeof fetch,
  firstBacktestId: number,
  secondBacktestId: number,
): Promise<RequestResult<BacktestComparison>> {
  return requestJson(fetchFunction, `${BACKTESTS_PATH}/${String(firstBacktestId)}/comparison/${String(secondBacktestId)}`);
}
