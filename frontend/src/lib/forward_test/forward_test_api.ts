// Calls the forward test routes and reads /ws/forward-tests (backend/src/atrade/forward_test/http_routes.py).
// The Web process writes only the desired state. The forward-test worker writes the status (docs/architecture.md 12.3).
import type { components } from '#lib/api';

export type ForwardTest = components['schemas']['ForwardTestResponse'];
export type ForwardTestRequest = components['schemas']['StartForwardTestRequest'];
export type ForwardTestStatus = components['schemas']['ForwardTestStatus'];
export type ForwardTestComparison = components['schemas']['ForwardTestComparisonResponse'];
export type FillComparison = components['schemas']['FillComparisonResponse'];
export type Interruption = components['schemas']['InterruptionResponse'];
type BarPeriod = components['schemas']['BarPeriod'];
type ValidationError = components['schemas']['ValidationError'];

export type StartResult = { kind: 'started'; forwardTest: ForwardTest } | { kind: 'failed'; message: string };
export type StopResult = { kind: 'stop_requested' } | { kind: 'failed'; message: string };
export type SamePeriodBacktestResult = { kind: 'started'; backtestId: number } | { kind: 'failed'; message: string };
export type ComparisonResult = { kind: 'ok'; value: ForwardTestComparison } | { kind: 'failed'; message: string };

export const FORWARD_TESTS_SOCKET_PATH = '/ws/forward-tests';
const FORWARD_TESTS_PATH = '/api/forward-tests';

// The bar periods of IB live bars (docs/architecture.md section 12.1). A backtest has no such limit.
const LIVE_BAR_PERIODS: readonly string[] = [
  '1-SECOND', '5-SECOND', '15-SECOND', '30-SECOND',
  '1-MINUTE', '2-MINUTE', '3-MINUTE', '5-MINUTE', '10-MINUTE', '15-MINUTE', '20-MINUTE', '30-MINUTE',
  '1-HOUR', '2-HOUR', '3-HOUR', '4-HOUR', '8-HOUR',
  '1-DAY', '1-WEEK', '1-MONTH',
]; // prettier-ignore

const STATUS_LABELS: Record<ForwardTestStatus, string> = {
  starting: 'Starting',
  running: 'Running',
  stopping: 'Stopping',
  stopped: 'Stopped',
  stop_failed: 'Stop failed',
  failed: 'Failed',
};

export function isLiveBarPeriod(barPeriod: BarPeriod): boolean {
  return LIVE_BAR_PERIODS.includes(barPeriod);
}

export function describeForwardTestStatus(status: ForwardTestStatus): string {
  return STATUS_LABELS[status];
}

/** A stop is useful while the forward test holds a client ID: then it can have open orders. */
export function canStop(forwardTest: ForwardTest): boolean {
  return forwardTest.desired_state === 'running' && forwardTest.client_id !== null;
}

/** The same period backtest uses the start balance as its paper capital (docs/architecture/forward_test.md 12.10). */
export function canBacktestSamePeriod(forwardTest: ForwardTest): boolean {
  return forwardTest.start_balance_usd !== null;
}

export function readForwardTestsMessage(message: unknown): ForwardTest[] | null {
  if (typeof message !== 'object' || message === null || !('type' in message) || message.type !== 'forward_tests') {
    return null;
  }
  if (!('forward_tests' in message) || !Array.isArray(message.forward_tests)) {
    return null;
  }
  return message.forward_tests as ForwardTest[];
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

// A refused start has {"detail": "<reason>"}. A request that does not validate has a list of field errors.
function describeError(body: unknown, status: number): string {
  if (typeof body !== 'object' || body === null || !('detail' in body)) {
    return `HTTP status ${String(status)}.`;
  }
  if (typeof body.detail === 'string') {
    return body.detail;
  }
  const firstError = Array.isArray(body.detail) ? (body.detail[0] as ValidationError | undefined) : undefined;
  if (firstError === undefined) {
    return `HTTP status ${String(status)}.`;
  }
  return `${String(firstError.loc.at(-1))}: ${firstError.msg}`;
}

export async function startForwardTest(fetchFunction: typeof fetch, request: ForwardTestRequest): Promise<StartResult> {
  let response: Response;
  try {
    response = await fetchFunction(FORWARD_TESTS_PATH, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(request),
    });
  } catch {
    return { kind: 'failed', message: 'Backend not reachable. The forward test did not start.' };
  }
  const body = await readJson(response);
  if (!response.ok) {
    return { kind: 'failed', message: describeError(body, response.status) };
  }
  return { kind: 'started', forwardTest: body as ForwardTest };
}

export async function stopForwardTest(fetchFunction: typeof fetch, forwardTestId: number): Promise<StopResult> {
  let response: Response;
  try {
    response = await fetchFunction(`${FORWARD_TESTS_PATH}/${String(forwardTestId)}/stop`, { method: 'POST' });
  } catch {
    return { kind: 'failed', message: 'Backend not reachable. The forward test did not get the stop request.' };
  }
  if (!response.ok) {
    return { kind: 'failed', message: describeError(await readJson(response), response.status) };
  }
  return { kind: 'stop_requested' };
}

export async function startSamePeriodBacktest(
  fetchFunction: typeof fetch,
  forwardTestId: number,
): Promise<SamePeriodBacktestResult> {
  let response: Response;
  try {
    response = await fetchFunction(`${FORWARD_TESTS_PATH}/${String(forwardTestId)}/same-period-backtests`, {
      method: 'POST',
    });
  } catch {
    return { kind: 'failed', message: 'Backend not reachable. The backtest did not start.' };
  }
  const body = await readJson(response);
  if (!response.ok) {
    return { kind: 'failed', message: describeError(body, response.status) };
  }
  return { kind: 'started', backtestId: (body as { backtest_id: number }).backtest_id };
}

export async function readForwardTestComparison(
  fetchFunction: typeof fetch,
  forwardTestId: number,
  backtestId: number,
): Promise<ComparisonResult> {
  let response: Response;
  try {
    response = await fetchFunction(`${FORWARD_TESTS_PATH}/${String(forwardTestId)}/comparison/${String(backtestId)}`);
  } catch {
    return { kind: 'failed', message: 'Backend not reachable. The comparison is not available.' };
  }
  const body = await readJson(response);
  if (!response.ok) {
    return { kind: 'failed', message: describeError(body, response.status) };
  }
  return { kind: 'ok', value: body as ForwardTestComparison };
}
