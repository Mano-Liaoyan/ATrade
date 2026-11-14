// The parameter sweep tools of the AI assistant (docs/architecture/assistant.md 25.4.6). They only read: the user
// starts, cancels, and deletes each sweep on the sweep page, so the user controls the runs and the DSR trial count.
// - read_sweep_parameters gives the parameters that a sweep of a strategy version can change.
// - list_sweeps gives each sweep with its run count of each status.
// - read_sweep gives each run with its parameter values and the main metrics, in the grid order. A run without
//   metrics has null metrics. A sweep has at most 200 runs, so the result stays below the tool result limit.
import { defineTool, type ToolDefinition } from '@earendil-works/pi-coding-agent';
import { Type } from 'typebox';
import { answerResult, isSuccess, textResult } from './tool_results.ts';
import type { WebPortClient } from './web_port_client.ts';

const Id = Type.Integer({ minimum: 1 });

/** The metrics of each run that read_sweep keeps (backtest.md 10.9.2). read_backtest gives all metrics of a run. */
export const SWEEP_RUN_METRICS = [
  'total_return_percent',
  'cagr_percent',
  'sharpe_ratio',
  'sortino_ratio',
  'max_drawdown_percent',
  'profit_factor',
  'win_rate_percent',
  'trade_count',
] as const;

interface SweepRunBody {
  backtest_id: number;
  parameters: Record<string, unknown>;
  status: string;
  metrics: Record<string, unknown> | null;
}

type SweepBody = Record<string, unknown> & { runs?: SweepRunBody[] };

/** The read_sweep content: the sweep fields, and each run with its parameters, its status, and the main metrics. */
export function summarizeSweep(body: SweepBody): Record<string, unknown> {
  const { runs = [], ...sweep } = body;
  return {
    ...sweep,
    runs: runs.map((run) => ({
      backtest_id: run.backtest_id,
      parameters: run.parameters,
      status: run.status,
      metrics:
        run.metrics === null ? null : Object.fromEntries(SWEEP_RUN_METRICS.map((name) => [name, run.metrics?.[name] ?? null])),
    })),
    note: 'Each run counts as one trial in the DSR of the strategy. Call read_backtest with a backtest_id for all metrics.',
  };
}

export function createSweepTools(client: WebPortClient): ToolDefinition[] {
  return [
    defineTool({
      name: 'read_sweep_parameters',
      label: 'Read sweep parameters',
      description:
        'Reads the parameters that a parameter sweep of a strategy version can change: the keyword arguments of the ' +
        '__init__ of the StrategyConfig subclass with an int, float, or bool annotation and a constant default. ' +
        'An empty list means that the user cannot sweep this version.',
      parameters: Type.Object({ strategy_version_id: Id }),
      execute: async (_id, params, signal) => {
        const path = `/api/sweeps/parameters?strategy_version_id=${String(params.strategy_version_id)}`;
        return answerResult(await client.request('GET', path, undefined, signal));
      },
    }),
    defineTool({
      name: 'list_sweeps',
      label: 'List parameter sweeps',
      description:
        'Lists the parameter sweeps that the user started, the newest first: the strategy version, the grid, the run ' +
        'count, and the run count of each status. The AI assistant cannot start a sweep. Ask the user to start one ' +
        'on the Parameter sweeps page.',
      parameters: Type.Object({}),
      execute: async (_id, _params, signal) => answerResult(await client.request('GET', '/api/sweeps', undefined, signal)),
    }),
    defineTool({
      name: 'read_sweep',
      label: 'Read parameter sweep',
      description:
        'Reads one parameter sweep: the grid and each run with its parameter values, status, and main metrics. ' +
        'Use it to tell if near parameter values give similar results. A good sweep has a wide area of good ' +
        'results, not one high point.',
      parameters: Type.Object({ sweep_id: Id }),
      execute: async (_id, params, signal) => {
        const answer = await client.request('GET', `/api/sweeps/${String(params.sweep_id)}`, undefined, signal);
        return isSuccess(answer) ? textResult(summarizeSweep(answer.body as SweepBody)) : answerResult(answer);
      },
    }),
  ];
}
