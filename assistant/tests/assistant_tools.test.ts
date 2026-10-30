// The strategy and backtest tools (docs/architecture/assistant.md 25.4.1, 25.4.2, 25.10). The fake model server
// calls the tools. The tools call a fake of port 8001. No real model provider and no real web.
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { afterEach, beforeEach, describe, expect, test } from 'vite-plus/test';
import { createAssistantTools } from '../src/assistant_tools.ts';
import { summarizeBacktest, type BacktestWait } from '../src/backtest_tools.ts';
import { Conversations, type RunEvent } from '../src/conversations.ts';
import { WebPortClient } from '../src/web_port_client.ts';
import { createFakeOpenModel } from './fake_model.ts';
import { startFakeModelServer, type ChatMessage, type FakeModelServer, type ModelStep } from './fake_model_server.ts';
import {
  backtestBody,
  COMPARISON,
  NO_SAVED_BARS,
  startFakeWebPort,
  STRATEGY,
  STRATEGY_LIST,
  versionBody,
  type FakeWebPort,
} from './fake_web_port.ts';

const SELECTION = { provider: 'fake', model: 'fake-model', credentialId: 'fake-key-1' };
const CONVERSATION_ID = '7';
const QUICK_WAIT: BacktestWait = { limitMilliseconds: 10_000, pollMilliseconds: 1, now: () => Date.now() };
const BACKTEST_ARGUMENTS = {
  strategy_version_id: 102,
  symbol: 'AAPL',
  exchange: 'NASDAQ',
  currency: 'USD',
  bar_period: '1-DAY',
  start_utc: '2026-03-01T00:00:00Z',
  end_utc: '2026-04-01T00:00:00Z',
  paper_capital_usd: 10000,
};

let workDir: string;
let model: FakeModelServer | undefined;
let web: FakeWebPort;

beforeEach(async () => {
  workDir = mkdtempSync(path.join(tmpdir(), 'atrade-assistant-'));
  web = await startFakeWebPort();
});

afterEach(async () => {
  await model?.close();
  model = undefined;
  await web.close();
  rmSync(workDir, { recursive: true, force: true });
});

async function openConversations(script: ModelStep[], wait: BacktestWait = QUICK_WAIT): Promise<Conversations> {
  model = await startFakeModelServer(script);
  const openModel = await createFakeOpenModel(model.baseUrl, workDir);
  return new Conversations({
    piDir: workDir,
    openModel,
    createTools: ({ conversationId, budget }) =>
      createAssistantTools({ client: new WebPortClient(web.baseUrl, conversationId), budget, wait }),
  });
}

async function runOnce(conversations: Conversations, text = 'Start.'): Promise<RunEvent[]> {
  const events: RunEvent[] = [];
  await conversations.run(CONVERSATION_ID, { text, selection: SELECTION, systemPrompt: 'You are the ATrade strategy assistant.' }, (event) => events.push(event));
  return events;
}

function call(toolName: string, toolArguments: Record<string, unknown> = {}): ModelStep {
  return { toolName, toolArguments };
}

/** The tool results that the model got, in order, as the parsed text. */
function readToolResults(): unknown[] {
  const messages: ChatMessage[] = model?.requests.at(-1)?.messages ?? [];
  return messages
    .filter((message) => message.role === 'tool')
    .map((message) => {
      const text = typeof message.content === 'string' ? message.content : JSON.stringify(message.content);
      try {
        return JSON.parse(text) as unknown;
      } catch {
        return text;
      }
    });
}

function eventsOfType<T extends RunEvent['type']>(events: RunEvent[], type: T) {
  return events.filter((event): event is Extract<RunEvent, { type: T }> => event.type === type);
}

describe('the strategy and backtest tools', () => {
  test('each tool calls port 8001 with the conversation and returns the content of 25.4.1', async () => {
    web.backtestStatuses = ['finished'];
    const conversations = await openConversations([
      call('list_strategies'),
      call('read_strategy', { strategy_id: 3 }),
      call('read_strategy_version', { strategy_id: 3, version_number: 2 }),
      call('create_strategy', { name: 'Momentum' }),
      call('save_strategy_version', { strategy_id: 3, code: '# new code\n' }),
      call('run_backtest', BACKTEST_ARGUMENTS),
      call('list_backtests'),
      call('read_backtest', { backtest_id: 11 }),
      call('compare_backtests', { first_backtest_id: 11, second_backtest_id: 12 }),
      { text: 'Done.' },
    ]);

    await runOnce(conversations);

    expect(web.requests.map((request) => `${request.method} ${request.path}`)).toEqual([
      'GET /api/strategies',
      'GET /api/strategies/3',
      'GET /api/strategies/3/versions/2',
      'POST /api/strategies',
      'POST /api/strategies/3/versions',
      'POST /api/backtests',
      'GET /api/backtests/11',
      'GET /api/backtests',
      'GET /api/backtests/11',
      'GET /api/backtests/11/comparison/12',
    ]);
    expect(web.requests.every((request) => request.conversationId === CONVERSATION_ID)).toBe(true);
    expect(web.requests[5]?.body).toEqual(BACKTEST_ARGUMENTS);
    const version = versionBody(2);
    const readBacktestContent = summarizeBacktest(backtestBody(11, 'finished'));
    expect(readToolResults()).toEqual([
      STRATEGY_LIST,
      STRATEGY,
      { id: version.id, strategy_id: 3, version_number: 2, source: 'user', code: version.code },
      { ...STRATEGY, id: 4 },
      expect.objectContaining({ id: 103, source: 'ai_assistant', conversation_id: 7 }),
      readBacktestContent,
      [backtestBody(11, 'finished')],
      readBacktestContent,
      COMPARISON,
    ]);
  });

  test('read_backtest returns at most 50 points of the equity curve and the first 50 trades', () => {
    const summary = summarizeBacktest(backtestBody(11, 'finished'));

    expect(summary.equity_curve_point_count).toBe(120);
    expect(summary.equity_curve).toHaveLength(50);
    expect((summary.equity_curve as { time_utc: string }[]).at(0)?.time_utc).toBe('point 0');
    expect((summary.equity_curve as { time_utc: string }[]).at(-1)?.time_utc).toBe('point 119');
    expect(summary.trade_count_total).toBe(60);
    expect(summary.trades).toHaveLength(50);
    expect(summary.metrics).toEqual({ final_equity_usd: '10500', trade_count: 60 });
  });

  test('save_strategy_version gives the problem list to the model, and the next save is announced', async () => {
    const problems = { problems: [{ line: 4, message: "F821 Undefined name 'sma'" }] };
    web.saveAnswers.push({ status: 422, body: problems });
    const conversations = await openConversations([
      call('save_strategy_version', { strategy_id: 3, code: 'bad' }),
      call('save_strategy_version', { strategy_id: 3, code: 'good' }),
      { text: 'Saved.' },
    ]);

    const events = await runOnce(conversations);

    const results = readToolResults();
    expect(results[0]).toBe(`Port 8001 answered 422: ${JSON.stringify(problems)}`);
    expect(results[1]).toEqual(expect.objectContaining({ id: 103, source: 'ai_assistant', conversation_id: 7 }));
    expect(web.requests.map((request) => request.conversationId)).toEqual([CONVERSATION_ID, CONVERSATION_ID]);
    expect(eventsOfType(events, 'strategy_version_saved')).toEqual([
      { type: 'strategy_version_saved', strategy_id: 3, strategy_version_id: 103, version_number: 3 },
    ]);
    expect(eventsOfType(events, 'tool_step').map((event) => event.status)).toEqual([
      'running',
      'failed',
      'running',
      'succeeded',
    ]);
  });

  test('read_strategy_version returns the rules only for a version of the rule builder', async () => {
    const conversations = await openConversations([
      call('read_strategy_version', { strategy_id: 3, version_number: 1 }),
      call('read_strategy_version', { strategy_id: 3, version_number: 2 }),
      { text: 'Read.' },
    ]);

    await runOnce(conversations);

    const [ruleBuilderVersion, userVersion] = readToolResults() as Record<string, unknown>[];
    expect(ruleBuilderVersion).toEqual(expect.objectContaining({ source: 'rule_builder', rules: versionBody(1).rules }));
    expect(userVersion).toEqual(expect.objectContaining({ source: 'user', code: versionBody(2).code }));
    expect(userVersion).not.toHaveProperty('rules');
  });
});

describe('run_backtest', () => {
  test('sends the queue state and the run state, then the read_backtest content and backtest_finished', async () => {
    const conversations = await openConversations([call('run_backtest', BACKTEST_ARGUMENTS), { text: 'Done.' }]);

    const events = await runOnce(conversations);

    const steps = eventsOfType(events, 'tool_step');
    expect(steps.map((step) => [step.status, step.backtest_id, step.backtest_status])).toEqual([
      ['running', null, null],
      ['running', 11, 'queued'],
      ['running', 11, 'running'],
      ['running', 11, 'finished'],
      ['succeeded', 11, 'finished'],
    ]);
    expect(steps.every((step) => step.tool_name === 'run_backtest' && step.tool_call_id === 'call_1')).toBe(true);
    expect(readToolResults()).toEqual([summarizeBacktest(backtestBody(11, 'finished'))]);
    expect(eventsOfType(events, 'backtest_finished')).toEqual([{ type: 'backtest_finished', backtest_id: 11 }]);
  });

  test('returns "still running" and the backtest ID after the wait limit, and the backtest continues', async () => {
    web.backtestStatuses = ['queued', 'running'];
    const shortWait: BacktestWait = { limitMilliseconds: 30, pollMilliseconds: 5, now: () => Date.now() };
    const conversations = await openConversations([call('run_backtest', BACKTEST_ARGUMENTS), { text: 'Later.' }], shortWait);

    const events = await runOnce(conversations);

    expect(readToolResults()).toEqual([
      'Backtest 11 is still running (status running). Read the result later with read_backtest.',
    ]);
    expect(eventsOfType(events, 'backtest_finished')).toEqual([]);
    expect(eventsOfType(events, 'tool_step').at(-1)).toEqual(
      expect.objectContaining({ status: 'succeeded', backtest_id: 11, backtest_status: 'running' }),
    );
    expect(web.requests.filter((request) => request.method !== 'GET')).toHaveLength(1);
  });

  test('starts at most 5 backtests for one user message, and 5 again for the next message', async () => {
    web.backtestStatuses = ['finished'];
    const sixCalls = Array.from({ length: 6 }, () => call('run_backtest', BACKTEST_ARGUMENTS));
    const conversations = await openConversations([
      ...sixCalls,
      { text: 'I ask the user.' },
      call('run_backtest', BACKTEST_ARGUMENTS),
      { text: 'Started one more.' },
    ]);

    await runOnce(conversations, 'Test 6 variants.');
    const sixthResult = readToolResults().at(-1);
    const startsOfFirstMessage = web.requests.filter((request) => request.method === 'POST').length;
    await runOnce(conversations, 'Yes, run more.');

    expect(startsOfFirstMessage).toBe(5);
    expect(sixthResult).toBe(
      'This user message already started 5 backtests. No backtest started. Ask the user before you start more backtests.',
    );
    expect(web.requests.filter((request) => request.method === 'POST')).toHaveLength(6);
  });

  test('gives the 422 of a range without saved bars to the model', async () => {
    web.hasNoSavedBars = true;
    const conversations = await openConversations([call('run_backtest', BACKTEST_ARGUMENTS), { text: 'No bars.' }]);

    const events = await runOnce(conversations);

    expect(readToolResults()).toEqual([`Port 8001 answered 422: ${JSON.stringify(NO_SAVED_BARS)}`]);
    expect(eventsOfType(events, 'tool_step').at(-1)?.status).toBe('failed');
  });
});
