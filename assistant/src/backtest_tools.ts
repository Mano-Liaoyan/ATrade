// run_backtest and read_backtest (docs/architecture/assistant.md 25.4.1, 25.4.2).
// - run_backtest calls POST /api/backtests on port 8001, then reads GET /api/backtests/{id} until the backtest ends,
//   at most 15 minutes. It sends each new queue state or run state with onUpdate. After 15 minutes it returns
//   "still running" and the backtest ID. The backtest continues.
// - One user message starts at most 5 backtests. The sixth call starts no backtest and returns an error.
// - A `screen` universe without a rebalance period rebalances each quarter. Each result of a fixed `list` universe
//   has the survivorship bias warning.
// - read_backtest returns the backtest with a summary of the equity curve and of the trades.
// - read_backtest and list_backtests add `error_summary`, the last line of the error message, to a failed backtest.
import type { AgentToolUpdateCallback } from '@earendil-works/pi-coding-agent';
import { answerResult, errorResult, isSuccess, textResult, type ToolDetails, type ToolResult } from './tool_results.ts';
import type { WebPortAnswer, WebPortClient } from './web_port_client.ts';

export const MAX_BACKTESTS_PER_USER_MESSAGE = 5;
export const MAX_EQUITY_POINTS = 50;
export const MAX_TRADES = 50;
const FINAL_STATUSES = new Set(['finished', 'failed', 'timed_out']);
const MILLISECONDS_PER_MINUTE = 60_000;
const WAIT_MINUTES = 15;
const POLL_MILLISECONDS = 2_000;
const DEFAULT_REBALANCE_PERIOD = 'quarter';

/** The warning in each run_backtest result of a fixed `list` universe (docs/architecture/assistant.md 25.4.2). */
export const SURVIVORSHIP_BIAS_WARNING =
  'Survivorship bias: this fixed list comes from a screen result at the end of the range, so it has no ' +
  'instruments that stopped trading in the range. The metrics can be too good. Write this warning in your answer.';

export interface BacktestWait {
  /** The longest wait for the end of a backtest. 15 minutes in the service. */
  limitMilliseconds: number;
  pollMilliseconds: number;
  now: () => number;
}

export const SERVICE_BACKTEST_WAIT: BacktestWait = {
  limitMilliseconds: WAIT_MINUTES * MILLISECONDS_PER_MINUTE,
  pollMilliseconds: POLL_MILLISECONDS,
  now: () => Date.now(),
};

/** The backtests that the current user message started. A new user message (prompt or steer) resets the count. */
export interface UserMessageBudget {
  startedBacktests: number;
}

interface BacktestState {
  id: number;
  status: string;
}

type DetailBody = Record<string, unknown> & { equity_curve?: unknown[]; trades?: unknown[] };

/** At most `count` items, evenly spread, with the first and the last item. */
export function spreadSample<T>(items: readonly T[], count: number): T[] {
  if (items.length <= count) {
    return [...items];
  }
  const step = (items.length - 1) / (count - 1);
  return Array.from({ length: count }, (_unused, index) => items[Math.round(index * step)] as T);
}

/** The last line of an error message that is not empty, for example the exception line of a traceback. */
export function findErrorSummary(errorMessage: unknown): string | null {
  if (typeof errorMessage !== 'string') {
    return null;
  }
  return errorMessage.split('\n').findLast((line) => line.trim() !== '')?.trim() ?? null;
}

/** A backtest with `error_summary` when it has an error message (docs/architecture/assistant.md 25.4.1). */
export function addErrorSummary<T extends Record<string, unknown>>(backtest: T): T & { error_summary?: string } {
  const summary = findErrorSummary(backtest.error_message);
  return summary === null ? backtest : { ...backtest, error_summary: summary };
}

/** The list_backtests content: the list of GET /api/backtests, each failed backtest with `error_summary`. */
export function summarizeBacktestList(body: unknown): unknown {
  if (!Array.isArray(body)) {
    return body;
  }
  return body.map((item: unknown) =>
    typeof item === 'object' && item !== null ? addErrorSummary(item as Record<string, unknown>) : item,
  );
}

/** The read_backtest content: all fields, the equity curve as at most 50 points, the first 50 trades, and
 * `error_summary` of a failed backtest. */
export function summarizeBacktest(body: DetailBody): Record<string, unknown> {
  const { equity_curve: equityCurve = [], trades = [], ...backtest } = body;
  return {
    ...addErrorSummary(backtest),
    equity_curve_point_count: equityCurve.length,
    equity_curve: spreadSample(equityCurve, MAX_EQUITY_POINTS),
    trade_count_total: trades.length,
    trades: trades.slice(0, MAX_TRADES),
  };
}

export async function readBacktest(client: WebPortClient, backtestId: number, signal?: AbortSignal) {
  const answer = await client.request('GET', `/api/backtests/${String(backtestId)}`, undefined, signal);
  if (!isSuccess(answer)) {
    return answerResult(answer);
  }
  return textResult(summarizeBacktest(answer.body as DetailBody));
}

function sleep(milliseconds: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    const timer = setTimeout(resolve, milliseconds);
    signal?.addEventListener('abort', () => {
      clearTimeout(timer);
      resolve();
    });
  });
}

function stateResult(state: BacktestState): ToolResult {
  return textResult(`Backtest ${String(state.id)}: ${state.status}.`, { backtest: state });
}

function stillRunningResult(state: BacktestState, warning: string | undefined): ToolResult {
  const text =
    `Backtest ${String(state.id)} is still running (status ${state.status}). ` +
    'Read the result later with read_backtest.' +
    (warning === undefined ? '' : ` ${warning}`);
  return textResult(text, { backtest: state });
}

/** The read_backtest content of a backtest with a final status, with the warning of a fixed list. */
async function finishedResult(
  client: WebPortClient,
  state: BacktestState,
  warning: string | undefined,
  signal?: AbortSignal,
): Promise<ToolResult> {
  const details = { backtest: state, finishedBacktestId: state.id };
  const answer = await client.request('GET', `/api/backtests/${String(state.id)}`, undefined, signal);
  if (!isSuccess(answer)) {
    return answerResult(answer, details);
  }
  const content = summarizeBacktest(answer.body as DetailBody);
  return textResult(warning === undefined ? content : { ...content, survivorship_bias_warning: warning }, details);
}

async function waitForEnd(
  client: WebPortClient,
  started: BacktestState,
  wait: BacktestWait,
  options: { warning?: string; signal?: AbortSignal; onUpdate?: AgentToolUpdateCallback<ToolDetails> },
): Promise<ToolResult> {
  const deadline = wait.now() + wait.limitMilliseconds;
  let state = started;
  options.onUpdate?.(stateResult(state));
  while (!FINAL_STATUSES.has(state.status)) {
    if (wait.now() >= deadline || options.signal?.aborted === true) {
      return stillRunningResult(state, options.warning);
    }
    await sleep(Math.min(wait.pollMilliseconds, Math.max(deadline - wait.now(), 0)), options.signal);
    const answer = await client.request('GET', `/api/backtests/${String(state.id)}`, undefined, options.signal);
    if (!isSuccess(answer)) {
      return answerResult(answer, { backtest: state });
    }
    const status = String((answer.body as DetailBody).status);
    if (status !== state.status) {
      state = { id: state.id, status };
      options.onUpdate?.(stateResult(state));
    }
  }
  return finishedResult(client, state, options.warning, options.signal);
}

/** The body of POST /api/backtests. A `screen` universe without a rebalance period rebalances each quarter. */
function toStartBody(request: Record<string, unknown>): Record<string, unknown> {
  if (request.universe_kind === 'screen' && request.rebalance_period === undefined) {
    return { ...request, rebalance_period: DEFAULT_REBALANCE_PERIOD };
  }
  return request;
}

export async function runBacktest(
  client: WebPortClient,
  request: Record<string, unknown>,
  context: {
    budget: UserMessageBudget;
    wait: BacktestWait;
    signal?: AbortSignal;
    onUpdate?: AgentToolUpdateCallback<ToolDetails>;
  },
): Promise<ToolResult> {
  if (context.budget.startedBacktests >= MAX_BACKTESTS_PER_USER_MESSAGE) {
    return errorResult(
      `This user message already started ${String(MAX_BACKTESTS_PER_USER_MESSAGE)} backtests. ` +
        'No backtest started. Ask the user before you start more backtests.',
    );
  }
  const body = toStartBody(request);
  // Count the backtest before the POST: pi runs the tool calls of one model turn in parallel.
  context.budget.startedBacktests += 1;
  let answer: WebPortAnswer;
  try {
    answer = await client.request('POST', '/api/backtests', body, context.signal);
  } catch (error) {
    context.budget.startedBacktests -= 1;
    throw error;
  }
  if (!isSuccess(answer)) {
    context.budget.startedBacktests -= 1;
    return answerResult(answer);
  }
  const started = answer.body as { id: number; status: string };
  // A fixed list is chosen at the end of the range (backtest section 10.10.6): its result always warns.
  const warning = body.universe_kind === 'list' ? SURVIVORSHIP_BIAS_WARNING : undefined;
  return waitForEnd(client, { id: started.id, status: started.status }, context.wait, { ...context, warning });
}
