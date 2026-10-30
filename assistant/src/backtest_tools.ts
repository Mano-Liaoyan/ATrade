// run_backtest and read_backtest (docs/architecture/assistant.md 25.4.1, 25.4.2).
// - run_backtest calls POST /api/backtests on port 8001, then reads GET /api/backtests/{id} until the backtest ends,
//   at most 15 minutes. It sends each new queue state or run state with onUpdate. After 15 minutes it returns
//   "still running" and the backtest ID. The backtest continues.
// - One user message starts at most 5 backtests. The sixth call starts no backtest and returns an error.
// - read_backtest returns the backtest with a summary of the equity curve and of the trades.
import type { AgentToolUpdateCallback } from '@earendil-works/pi-coding-agent';
import { answerResult, errorResult, isSuccess, textResult, type ToolDetails, type ToolResult } from './tool_results.ts';
import type { WebPortClient } from './web_port_client.ts';

export const MAX_BACKTESTS_PER_USER_MESSAGE = 5;
export const MAX_EQUITY_POINTS = 50;
export const MAX_TRADES = 50;
const FINAL_STATUSES = new Set(['finished', 'failed', 'timed_out']);
const MILLISECONDS_PER_MINUTE = 60_000;
const WAIT_MINUTES = 15;
const POLL_MILLISECONDS = 2_000;

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

/** The read_backtest content: all fields, the equity curve as at most 50 points, and the first 50 trades. */
export function summarizeBacktest(body: DetailBody): Record<string, unknown> {
  const { equity_curve: equityCurve = [], trades = [], ...backtest } = body;
  return {
    ...backtest,
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

function stillRunningResult(state: BacktestState): ToolResult {
  const text =
    `Backtest ${String(state.id)} is still running (status ${state.status}). ` +
    'Read the result later with read_backtest.';
  return textResult(text, { backtest: state });
}

async function waitForEnd(
  client: WebPortClient,
  started: BacktestState,
  wait: BacktestWait,
  options: { signal?: AbortSignal; onUpdate?: AgentToolUpdateCallback<ToolDetails> },
): Promise<ToolResult> {
  const deadline = wait.now() + wait.limitMilliseconds;
  let state = started;
  options.onUpdate?.(stateResult(state));
  while (!FINAL_STATUSES.has(state.status)) {
    if (wait.now() >= deadline || options.signal?.aborted === true) {
      return stillRunningResult(state);
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
  const read = await readBacktest(client, state.id, options.signal);
  return { ...read, details: { backtest: state, finishedBacktestId: state.id } };
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
  const answer = await client.request('POST', '/api/backtests', request, context.signal);
  if (!isSuccess(answer)) {
    return answerResult(answer);
  }
  context.budget.startedBacktests += 1;
  const body = answer.body as { id: number; status: string };
  return waitForEnd(client, { id: body.id, status: body.status }, context.wait, context);
}
