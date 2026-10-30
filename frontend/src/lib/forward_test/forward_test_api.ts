// Calls the forward test routes and reads /ws/forward-tests (backend/src/atrade/forward_test/http_routes.py).
// The Web process writes only the desired state. The forward-test worker writes the status (docs/architecture.md 12.3).
import type { components } from '#lib/api';
import type { StatusKind } from '#lib/foundation/carbon';
import { describeErrorBody, readJsonBody, sendRequest } from '#lib/foundation/http_request';
import { readSocketMessage } from '#lib/foundation/live_socket';

export type ForwardTest = components['schemas']['ForwardTestResponse'];
export type ForwardTestRequest = components['schemas']['StartForwardTestRequest'];
export type ForwardTestStatus = components['schemas']['ForwardTestStatus'];
export type ForwardTestComparison = components['schemas']['ForwardTestComparisonResponse'];
export type FillComparison = components['schemas']['FillComparisonResponse'];
export type ComparedInterruption = components['schemas']['ComparedInterruptionResponse'];
export type ForwardTestDetail = components['schemas']['ForwardTestDetailResponse'];
export type ForwardTestFill = components['schemas']['ForwardTestFillResponse'];
export type ForwardTestInterruption = components['schemas']['InterruptionResponse'];
type BarPeriod = components['schemas']['BarPeriod'];
type ForwardTestsMessage = components['schemas']['ForwardTestsMessage'];
type SamePeriodBacktestResponse = components['schemas']['SamePeriodBacktestResponse'];

export type StartResult = { kind: 'started'; forwardTest: ForwardTest } | { kind: 'failed'; message: string };
export type StopResult = { kind: 'stop_requested' } | { kind: 'failed'; message: string };
export type SamePeriodBacktestResult = { kind: 'started'; backtestId: number } | { kind: 'failed'; message: string };
export type ComparisonResult = { kind: 'ok'; value: ForwardTestComparison } | { kind: 'failed'; message: string };
export type DetailResult = { kind: 'ok'; value: ForwardTestDetail } | { kind: 'failed'; message: string };

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
  waiting_for_gateway: 'Waiting for IB Gateway',
  stopping: 'Stopping',
  stopped: 'Stopped',
  stop_failed: 'Stop failed',
  failed: 'Failed',
};

// The icon and the color of each status (AGENTS.md: a status shows an icon and a word together with its color).
const STATUS_KINDS: Record<ForwardTestStatus, StatusKind> = {
  starting: 'in-progress',
  running: 'success',
  waiting_for_gateway: 'warning',
  stopping: 'in-progress',
  stopped: 'neutral',
  stop_failed: 'error',
  failed: 'error',
};

const INTERRUPTION_REASON_LABELS: Record<ForwardTestInterruption['reason'], string> = {
  crash: 'Crash',
  gateway: 'IB Gateway not reachable',
  worker_restart: 'Worker restart',
};

export function isLiveBarPeriod(barPeriod: BarPeriod): boolean {
  return LIVE_BAR_PERIODS.includes(barPeriod);
}

export function describeForwardTestStatus(status: ForwardTestStatus): string {
  return STATUS_LABELS[status];
}

// The universe name of a multi-instrument forward test for the page header (section 12.16). Null for one instrument.
export function describeForwardTestUniverse(forwardTest: ForwardTest): string | null {
  if (forwardTest.universe_kind === 'rule') {
    return `Top ${String(forwardTest.universe_top_n)} by trading value`;
  }
  return forwardTest.universe_kind === 'list' ? 'Watchlist' : null;
}

// The instrument of a single-instrument forward test. Null for a multi-instrument forward test.
export function readForwardTestInstrument(
  forwardTest: ForwardTest,
): { symbol: string; exchange: string; currency: string } | null {
  const { symbol, exchange, currency } = forwardTest;
  return symbol === null || exchange === null || currency === null ? null : { symbol, exchange, currency };
}

export function findForwardTestStatusKind(status: ForwardTestStatus): StatusKind {
  return STATUS_KINDS[status];
}

export function describeInterruptionReason(reason: ForwardTestInterruption['reason']): string {
  return INTERRUPTION_REASON_LABELS[reason];
}

/**
 * The value of a datetime-local input is a local time without a time zone. The API takes UTC (section 12.1).
 * Returns null for an empty input: the forward test then runs until the user stops it.
 */
export function readEndTimeUtc(localValue: string): string | null {
  if (localValue === '') {
    return null;
  }
  const endTime = new Date(localValue);
  return Number.isNaN(endTime.getTime()) ? null : endTime.toISOString();
}

const TIME_PART_DIGITS = 2;

function padTwoDigits(value: number): string {
  return String(value).padStart(TIME_PART_DIGITS, '0');
}

/** Shows a UTC time of the API in the local time zone of the browser, like "2026-01-03 09:30". */
export function formatLocalTime(utcTime: string | null): string {
  if (utcTime === null) {
    return '';
  }
  const time = new Date(utcTime);
  const date = `${String(time.getFullYear())}-${padTwoDigits(time.getMonth() + 1)}-${padTwoDigits(time.getDate())}`;
  return `${date} ${padTwoDigits(time.getHours())}:${padTwoDigits(time.getMinutes())}`;
}

/** A stopped forward test has no crash count as its current state. Its crash interruptions are the history. */
export function showsCrashCount(forwardTest: ForwardTest): boolean {
  return forwardTest.crash_count > 0 && forwardTest.status !== 'stopped';
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
  return readSocketMessage<ForwardTestsMessage>(message, ['forward_tests'])?.forward_tests ?? null;
}

type RequestOutcome = { kind: 'ok'; body: unknown } | { kind: 'failed'; message: string };

// A refused request has {"detail": "<reason>"}. A request that does not validate has a list of field errors.
async function sendForwardTestRequest(
  fetchFunction: typeof fetch,
  path: string,
  init: RequestInit | undefined,
  messages: { notReachable: string; failedAction: string },
): Promise<RequestOutcome> {
  const response = await sendRequest(fetchFunction, path, init);
  if (response === null) {
    return { kind: 'failed', message: messages.notReachable };
  }
  const body = await readJsonBody(response);
  if (!response.ok) {
    return { kind: 'failed', message: describeErrorBody(body, response.status, messages.failedAction) };
  }
  return { kind: 'ok', body };
}

export async function startForwardTest(fetchFunction: typeof fetch, request: ForwardTestRequest): Promise<StartResult> {
  const outcome = await sendForwardTestRequest(
    fetchFunction,
    FORWARD_TESTS_PATH,
    { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(request) },
    { notReachable: 'Backend not reachable. The forward test did not start.', failedAction: 'Starting the forward test' },
  );
  if (outcome.kind === 'failed') {
    return outcome;
  }
  return { kind: 'started', forwardTest: outcome.body as ForwardTest };
}

export async function stopForwardTest(fetchFunction: typeof fetch, forwardTestId: number): Promise<StopResult> {
  const outcome = await sendForwardTestRequest(
    fetchFunction,
    `${FORWARD_TESTS_PATH}/${String(forwardTestId)}/stop`,
    { method: 'POST' },
    {
      notReachable: 'Backend not reachable. The forward test did not get the stop request.',
      failedAction: 'The stop request',
    },
  );
  if (outcome.kind === 'failed') {
    return outcome;
  }
  return { kind: 'stop_requested' };
}

export async function startSamePeriodBacktest(
  fetchFunction: typeof fetch,
  forwardTestId: number,
): Promise<SamePeriodBacktestResult> {
  const outcome = await sendForwardTestRequest(
    fetchFunction,
    `${FORWARD_TESTS_PATH}/${String(forwardTestId)}/same-period-backtests`,
    { method: 'POST' },
    { notReachable: 'Backend not reachable. The backtest did not start.', failedAction: 'Starting the backtest' },
  );
  if (outcome.kind === 'failed') {
    return outcome;
  }
  return { kind: 'started', backtestId: (outcome.body as SamePeriodBacktestResponse).backtest_id };
}

export async function readForwardTestComparison(
  fetchFunction: typeof fetch,
  forwardTestId: number,
  backtestId: number,
): Promise<ComparisonResult> {
  const outcome = await sendForwardTestRequest(
    fetchFunction,
    `${FORWARD_TESTS_PATH}/${String(forwardTestId)}/comparison/${String(backtestId)}`,
    undefined,
    { notReachable: 'Backend not reachable. The comparison is not available.', failedAction: 'Reading the comparison' },
  );
  if (outcome.kind === 'failed') {
    return outcome;
  }
  return { kind: 'ok', value: outcome.body as ForwardTestComparison };
}

export async function readForwardTestDetail(fetchFunction: typeof fetch, forwardTestId: number): Promise<DetailResult> {
  const outcome = await sendForwardTestRequest(
    fetchFunction,
    `${FORWARD_TESTS_PATH}/${String(forwardTestId)}`,
    undefined,
    { notReachable: 'Backend not reachable. The forward test is not available.', failedAction: 'Reading the forward test' },
  );
  if (outcome.kind === 'failed') {
    return outcome;
  }
  return { kind: 'ok', value: outcome.body as ForwardTestDetail };
}
