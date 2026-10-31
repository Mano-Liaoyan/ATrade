// The tools of the AI assistant (docs/architecture/assistant.md 25.4.1). pi may run only these tools.
// Each tool calls only the routes of port 8001 of web (25.3.3). The screen tools of 25.4.3 are in screen_tools.ts.
import { defineTool, type ToolDefinition } from '@earendil-works/pi-coding-agent';
import { Type } from 'typebox';
import { readBacktest, runBacktest, type BacktestWait, type UserMessageBudget } from './backtest_tools.ts';
import { createScreenTools } from './screen_tools.ts';
import { answerResult, isSuccess, textResult } from './tool_results.ts';
import type { WebPortClient } from './web_port_client.ts';

export const ASSISTANT_TOOL_NAMES: readonly string[] = [
  'list_strategies',
  'read_strategy',
  'read_strategy_version',
  'create_strategy',
  'save_strategy_version',
  'run_backtest',
  'list_backtests',
  'read_backtest',
  'compare_backtests',
  'list_screens',
  'read_screen',
  'create_screen',
  'update_screen',
  'run_screen',
  'read_screen_result',
];

export interface AssistantToolsContext {
  /** The client of port 8001 with the conversation ID of the run. */
  client: WebPortClient;
  budget: UserMessageBudget;
  wait: BacktestWait;
}

// A save of new code answers 201. A save of the code of the latest version answers 200 and saves nothing.
const HTTP_CREATED = 201;
const Id = Type.Integer({ minimum: 1 });
const BAR_PERIODS = ['1-MINUTE', '5-MINUTE', '15-MINUTE', '30-MINUTE', '1-HOUR', '1-DAY'] as const;
// Not `rule` and not the watchlist (docs/architecture/backtest.md 10.10.8): the AI assistant backtests a screen.
const UNIVERSE_KINDS = ['single', 'screen', 'list'] as const;
const REBALANCE_PERIODS = ['quarter', 'month'] as const;

interface VersionBody {
  id: number;
  strategy_id: number;
  version_number: number;
  source: string;
  code: string;
  rules: unknown;
}

/** The code of a version. The rules JSON only for a version of the rule builder (ADR 0006). */
function toVersionContent(version: VersionBody): Record<string, unknown> {
  const content: Record<string, unknown> = {
    id: version.id,
    strategy_id: version.strategy_id,
    version_number: version.version_number,
    source: version.source,
    code: version.code,
  };
  if (version.source === 'rule_builder') {
    content.rules = version.rules;
  }
  return content;
}

function createStrategyTools(context: AssistantToolsContext): ToolDefinition[] {
  const { client } = context;
  return [
    defineTool({
      name: 'list_strategies',
      label: 'List strategies',
      description: 'Lists the strategies: ID, name, and latest version number.',
      parameters: Type.Object({}),
      execute: async (_id, _params, signal) => answerResult(await client.request('GET', '/api/strategies', undefined, signal)),
    }),
    defineTool({
      name: 'read_strategy',
      label: 'Read strategy',
      description: 'Reads one strategy and its version list.',
      parameters: Type.Object({ strategy_id: Id }),
      execute: async (_id, params, signal) =>
        answerResult(await client.request('GET', `/api/strategies/${String(params.strategy_id)}`, undefined, signal)),
    }),
    defineTool({
      name: 'read_strategy_version',
      label: 'Read strategy version',
      description:
        'Reads the code of one strategy version. For a version of the rule builder, also its rules JSON. ' +
        'Change only the code, never the rules.',
      parameters: Type.Object({ strategy_id: Id, version_number: Id }),
      execute: async (_id, params, signal) => {
        const path = `/api/strategies/${String(params.strategy_id)}/versions/${String(params.version_number)}`;
        const answer = await client.request('GET', path, undefined, signal);
        return isSuccess(answer) ? textResult(toVersionContent(answer.body as VersionBody)) : answerResult(answer);
      },
    }),
    defineTool({
      name: 'create_strategy',
      label: 'Create strategy',
      description: 'Creates a strategy with version 1 from the template.',
      parameters: Type.Object({ name: Type.String({ minLength: 1 }) }),
      execute: async (_id, params, signal) =>
        answerResult(await client.request('POST', '/api/strategies', { name: params.name }, signal)),
    }),
    defineTool({
      name: 'save_strategy_version',
      label: 'Save strategy version',
      description:
        'Saves Python code as a new version of a strategy. When the checks before save fail, the result is the ' +
        'problem list {"problems": [{"line", "message"}]}. Correct the code and save again.',
      parameters: Type.Object({ strategy_id: Id, code: Type.String() }),
      execute: async (_id, params, signal) => {
        const path = `/api/strategies/${String(params.strategy_id)}/versions`;
        const answer = await client.request('POST', path, { code: params.code }, signal);
        const version = answer.body as VersionBody;
        const isNewVersion = answer.status === HTTP_CREATED;
        const savedVersion = isNewVersion
          ? { strategy_id: version.strategy_id, strategy_version_id: version.id, version_number: version.version_number }
          : undefined;
        return answerResult(answer, savedVersion === undefined ? {} : { savedVersion });
      },
    }),
  ];
}

function createBacktestTools(context: AssistantToolsContext): ToolDefinition[] {
  const { client } = context;
  return [
    defineTool({
      name: 'run_backtest',
      label: 'Run backtest',
      description:
        'Queues a backtest of a saved strategy version and waits at most 15 minutes for its end. ' +
        'universe_kind "single" (the default) needs symbol, exchange, and currency. ' +
        '"screen" needs screen_id: the screen runs again at each rebalance_period start (quarter, the default, or ' +
        'month). Use "screen" for a backtest from a screen. ' +
        '"list" needs screen_result_id, and optionally symbols (a part of that screen result): a fixed list. ' +
        'A multi-instrument backtest needs 1-DAY or 1-HOUR bars. Only instruments and a bar period with saved bars ' +
        'can run. One user message can start at most 5 backtests.',
      parameters: Type.Object({
        strategy_version_id: Id,
        universe_kind: Type.Optional(Type.Union(UNIVERSE_KINDS.map((kind) => Type.Literal(kind)))),
        symbol: Type.Optional(Type.String({ minLength: 1 })),
        exchange: Type.Optional(Type.String({ minLength: 1 })),
        currency: Type.Optional(Type.String({ minLength: 1 })),
        screen_id: Type.Optional(Id),
        rebalance_period: Type.Optional(Type.Union(REBALANCE_PERIODS.map((period) => Type.Literal(period)))),
        screen_result_id: Type.Optional(Id),
        symbols: Type.Optional(Type.Array(Type.String({ minLength: 1 }), { minItems: 1, maxItems: 500 })),
        bar_period: Type.Union(BAR_PERIODS.map((period) => Type.Literal(period))),
        start_utc: Type.String({ description: 'ISO 8601 time with a time zone, for example 2026-01-02T00:00:00Z.' }),
        end_utc: Type.String({ description: 'ISO 8601 time with a time zone.' }),
        paper_capital_usd: Type.Number({ exclusiveMinimum: 0 }),
      }),
      execute: (_id, params, signal, onUpdate) =>
        runBacktest(client, params, { budget: context.budget, wait: context.wait, signal, onUpdate }),
    }),
    defineTool({
      name: 'list_backtests',
      label: 'List backtests',
      description: 'Lists the backtests with their instrument, bar period, status, and metrics.',
      parameters: Type.Object({}),
      execute: async (_id, _params, signal) => answerResult(await client.request('GET', '/api/backtests', undefined, signal)),
    }),
    defineTool({
      name: 'read_backtest',
      label: 'Read backtest',
      description: 'Reads one backtest: the metrics, at most 50 points of the equity curve, and the first 50 trades.',
      parameters: Type.Object({ backtest_id: Id }),
      execute: (_id, params, signal) => readBacktest(client, params.backtest_id, signal),
    }),
    defineTool({
      name: 'compare_backtests',
      label: 'Compare backtests',
      description: 'Compares 2 backtests of the same strategy.',
      parameters: Type.Object({ first_backtest_id: Id, second_backtest_id: Id }),
      execute: async (_id, params, signal) => {
        const path = `/api/backtests/${String(params.first_backtest_id)}/comparison/${String(params.second_backtest_id)}`;
        return answerResult(await client.request('GET', path, undefined, signal));
      },
    }),
  ];
}

/** The 9 tools of 25.4.1 and the 6 screen tools of 25.4.3 for one run of one conversation. */
export function createAssistantTools(context: AssistantToolsContext): ToolDefinition[] {
  return [...createStrategyTools(context), ...createBacktestTools(context), ...createScreenTools(context.client)];
}
