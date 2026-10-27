// Calls the backtest HTTP routes (backend/src/atrade/backtest/http_routes.py).

import type { components } from '#lib/api';

export type BacktestRequest = components['schemas']['StartBacktestRequest'];
export type Backtest = components['schemas']['BacktestResponse'];
export type BacktestDetail = components['schemas']['BacktestDetailResponse'];
export type BacktestStatus = components['schemas']['BacktestStatus'];
export type BacktestMetrics = components['schemas']['BacktestMetricsResponse'];
export type EquityPoint = components['schemas']['EquityPointResponse'];
export type BacktestTrade = components['schemas']['TradeResponse'];
export type BacktestComparison = components['schemas']['BacktestComparisonResponse'];
type ValidationError = components['schemas']['ValidationError'];

export type RequestResult<T> = { kind: 'ok'; value: T } | { kind: 'failed'; message: string };

const BACKTESTS_PATH = '/api/backtests';
const BACKEND_NOT_REACHABLE = 'The backend is not reachable.';

async function sendRequest(fetchFunction: typeof fetch, path: string, init?: RequestInit): Promise<Response | null> {
  try {
    return await fetchFunction(path, init);
  } catch {
    return null;
  }
}

// A refused request has {"detail": "<reason>"}. A request that does not validate has a list of field errors.
function describeFailure(failure: { detail?: string | ValidationError[] }, statusCode: number): string {
  const detail = failure.detail;
  if (typeof detail === 'string') {
    return detail;
  }
  const firstError = detail?.[0];
  if (firstError === undefined) {
    return `Request failed with status ${String(statusCode)}.`;
  }
  const fieldName = firstError.loc.at(-1);
  return `${String(fieldName)}: ${firstError.msg}`;
}

async function readFailureMessage(response: Response): Promise<string> {
  try {
    return describeFailure((await response.json()) as { detail?: string | ValidationError[] }, response.status);
  } catch {
    return `Request failed with status ${String(response.status)}.`;
  }
}

async function requestJson<T>(fetchFunction: typeof fetch, path: string, init?: RequestInit): Promise<RequestResult<T>> {
  const response = await sendRequest(fetchFunction, path, init);
  if (response === null) {
    return { kind: 'failed', message: BACKEND_NOT_REACHABLE };
  }
  if (!response.ok) {
    return { kind: 'failed', message: await readFailureMessage(response) };
  }
  return { kind: 'ok', value: (await response.json()) as T };
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

export function compareBacktests(
  fetchFunction: typeof fetch,
  firstBacktestId: number,
  secondBacktestId: number,
): Promise<RequestResult<BacktestComparison>> {
  return requestJson(fetchFunction, `${BACKTESTS_PATH}/${String(firstBacktestId)}/comparison/${String(secondBacktestId)}`);
}
