// The strategy and backtest tools (docs/architecture/assistant.md 25.4.1, 25.4.2, 25.10). The fake model server
// calls the tools. The tools call a fake of port 8001. No real model provider and no real web.
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { afterEach, beforeEach, describe, expect, test } from 'vite-plus/test';
import { createAssistantTools } from '../src/assistant_tools.ts';
import { runBacktest, summarizeBacktest, SURVIVORSHIP_BIAS_WARNING, type BacktestWait } from '../src/backtest_tools.ts';
import { Conversations, type RunEvent } from '../src/conversations.ts';
import { WebPortClient } from '../src/web_port_client.ts';
import { createFakeOpenModel } from './fake_model.ts';
import { startFakeModelServer, type ChatMessage, type FakeModelServer, type ModelStep } from './fake_model_server.ts';
import {
  backtestBody,
  COMPARISON,
  NO_SAVED_BARS,
  SCREEN,
  SCREEN_DEFINITION,
  SCREEN_LIST,
  SOURCE_SCREEN,
  STRATEGY_TRACEBACK,
  SCREEN_SUMMARY,
  screenRow,
  startFakeWebPort,
  STRATEGY,
  STRATEGY_LIST,
  versionBody,
  type FakeWebPort,
  type WebPortRequest,
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
  await conversations.run(CONVERSATION_ID, { text, selection: SELECTION, thinkingLevel: 'off', systemPrompt: 'You help with strategies.' }, (event) => events.push(event));
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

  test('read_backtest and list_backtests give the last error line of a failed backtest as error_summary', async () => {
    web.backtestStatuses = ['failed'];
    web.backtestList = [backtestBody(12, 'failed'), backtestBody(11, 'finished')];
    const conversations = await openConversations([
      call('list_backtests'),
      call('read_backtest', { backtest_id: 12 }),
      { text: 'Read.' },
    ]);

    await runOnce(conversations);

    const [listed, read] = readToolResults() as [Record<string, unknown>[], Record<string, unknown>];
    const lastLine = "AttributeError: 'MovingAverageStrategy' object has no attribute 'id'";
    expect(listed[0]).toEqual(expect.objectContaining({ id: 12, error_summary: lastLine }));
    expect(listed[1]).not.toHaveProperty('error_summary');
    expect(read).toEqual(expect.objectContaining({ id: 12, error_message: STRATEGY_TRACEBACK, error_summary: lastLine }));
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

  test('starts at most 5 backtests when one model turn calls run_backtest 6 times in parallel', async () => {
    web.backtestStatuses = ['finished'];
    const budget = { startedBacktests: 0 };
    const client = new WebPortClient(web.baseUrl, CONVERSATION_ID);

    const results = await Promise.all(
      Array.from({ length: 6 }, () => runBacktest(client, BACKTEST_ARGUMENTS, { budget, wait: QUICK_WAIT })),
    );

    expect(web.requests.filter((request) => request.method === 'POST')).toHaveLength(5);
    expect(results.filter((result) => result.isError === true)).toHaveLength(1);
    expect(budget.startedBacktests).toBe(5);
  });

  test('a backtest that port 8001 refuses does not count', async () => {
    web.hasNoSavedBars = true;
    const budget = { startedBacktests: 0 };

    await runBacktest(new WebPortClient(web.baseUrl, CONVERSATION_ID), BACKTEST_ARGUMENTS, { budget, wait: QUICK_WAIT });

    expect(budget.startedBacktests).toBe(0);
  });

  test('gives the 422 of a range without saved bars to the model', async () => {
    web.hasNoSavedBars = true;
    const conversations = await openConversations([call('run_backtest', BACKTEST_ARGUMENTS), { text: 'No bars.' }]);

    const events = await runOnce(conversations);

    expect(readToolResults()).toEqual([`Port 8001 answered 422: ${JSON.stringify(NO_SAVED_BARS)}`]);
    expect(eventsOfType(events, 'tool_step').at(-1)?.status).toBe('failed');
  });
});

const SCREEN_BACKTEST_ARGUMENTS = {
  strategy_version_id: 102,
  universe_kind: 'screen',
  screen_id: 5,
  bar_period: '1-DAY',
  start_utc: '2018-01-01T00:00:00Z',
  end_utc: '2026-01-01T00:00:00Z',
  paper_capital_usd: 100000,
};
const LIST_BACKTEST_ARGUMENTS = {
  strategy_version_id: 102,
  universe_kind: 'list',
  screen_result_id: 9,
  symbols: ['S1', 'S2'],
  bar_period: '1-DAY',
  start_utc: '2018-01-01T00:00:00Z',
  end_utc: '2026-01-01T00:00:00Z',
  paper_capital_usd: 100000,
};

function backtestStarts(): WebPortRequest[] {
  return web.requests.filter((request) => request.method === 'POST' && request.path === '/api/backtests');
}

describe('run_backtest with a universe (25.4.2)', () => {
  test('starts a screen backtest with the conversation and each quarter when no period is given', async () => {
    const conversations = await openConversations([
      call('run_backtest', SCREEN_BACKTEST_ARGUMENTS),
      call('run_backtest', { ...SCREEN_BACKTEST_ARGUMENTS, rebalance_period: 'month' }),
      { text: 'Done.' },
    ]);

    await runOnce(conversations);

    expect(backtestStarts().map((request) => [request.conversationId, request.body])).toEqual([
      [CONVERSATION_ID, { ...SCREEN_BACKTEST_ARGUMENTS, rebalance_period: 'quarter' }],
      [CONVERSATION_ID, { ...SCREEN_BACKTEST_ARGUMENTS, rebalance_period: 'month' }],
    ]);
    expect(readToolResults()).toEqual([
      summarizeBacktest(backtestBody(11, 'finished')),
      summarizeBacktest(backtestBody(12, 'finished')),
    ]);
  });

  test('starts a fixed list backtest of a screen result, and each result has the survivorship bias warning', async () => {
    const conversations = await openConversations([
      call('run_backtest', LIST_BACKTEST_ARGUMENTS),
      { text: 'Done.' },
    ]);

    await runOnce(conversations);

    expect(backtestStarts().map((request) => [request.conversationId, request.body])).toEqual([
      [CONVERSATION_ID, LIST_BACKTEST_ARGUMENTS],
    ]);
    expect(readToolResults()).toEqual([
      { ...summarizeBacktest(backtestBody(11, 'finished')), survivorship_bias_warning: SURVIVORSHIP_BIAS_WARNING },
    ]);
    expect(SURVIVORSHIP_BIAS_WARNING).toContain('Write this warning in your answer');
  });

  test('returns "still running", the backtest ID, and the warning when a fixed list backtest passes the wait', async () => {
    web.backtestStatuses = ['queued', 'running'];
    const shortWait: BacktestWait = { limitMilliseconds: 30, pollMilliseconds: 5, now: () => Date.now() };
    const conversations = await openConversations(
      [call('run_backtest', LIST_BACKTEST_ARGUMENTS), { text: 'Later.' }],
      shortWait,
    );

    await runOnce(conversations);

    expect(readToolResults()).toEqual([
      'Backtest 11 is still running (status running). Read the result later with read_backtest. ' +
        SURVIVORSHIP_BIAS_WARNING,
    ]);
  });

  test('a multi-instrument backtest counts as 1 of the 5 backtests of a user message', async () => {
    web.backtestStatuses = ['finished'];
    const conversations = await openConversations([
      call('run_backtest', SCREEN_BACKTEST_ARGUMENTS),
      call('run_backtest', LIST_BACKTEST_ARGUMENTS),
      call('run_backtest', BACKTEST_ARGUMENTS),
      call('run_backtest', SCREEN_BACKTEST_ARGUMENTS),
      call('run_backtest', LIST_BACKTEST_ARGUMENTS),
      call('run_backtest', SCREEN_BACKTEST_ARGUMENTS),
      { text: 'I ask the user.' },
    ]);

    await runOnce(conversations, 'Test the screen.');

    expect(backtestStarts()).toHaveLength(5);
    expect(readToolResults().at(-1)).toBe(
      'This user message already started 5 backtests. No backtest started. Ask the user before you start more backtests.',
    );
  });
});

describe('the screen tools', () => {
  const DEFINITION = { start: 'quarter_universe', filters: [], indicator_conditions: [] };

  test('each tool calls port 8001 with the conversation (25.4.3)', async () => {
    const conversations = await openConversations([
      call('list_screens'),
      call('read_screen', { screen_id: 5 }),
      call('create_screen', { name: 'Momentum leaders', market: 'US', definition: DEFINITION }),
      call('update_screen', { screen_id: 5, name: 'Momentum leaders (AI)', definition: DEFINITION }),
      call('run_screen', { screen_id: 5 }),
      call('read_screen_result', { screen_result_id: 9 }),
      { text: 'Done.' },
    ]);

    await runOnce(conversations);

    expect(web.requests.map((request) => `${request.method} ${request.path}`)).toEqual([
      'GET /api/screens',
      'GET /api/screens/5',
      'POST /api/screens',
      // update_screen reads the screen before the change, for the condition card.
      'GET /api/screens/5',
      'PUT /api/screens/5',
      'POST /api/screens/5/runs',
      'GET /api/screen-results/9?offset=0&limit=50',
    ]);
    expect(web.requests.map((request) => request.conversationId)).toEqual(Array(7).fill(CONVERSATION_ID));
    expect(web.requests[2]?.body).toEqual({ name: 'Momentum leaders', market: 'US', definition: DEFINITION });
    expect(web.requests[4]?.body).toEqual({ name: 'Momentum leaders (AI)', definition: DEFINITION });
    const results = readToolResults();
    expect(results.slice(0, 4)).toEqual([SCREEN_LIST, SCREEN, SCREEN, SCREEN]);
  });

  test('create_screen and update_screen announce the screen for the condition card, with the definition before', async () => {
    const conversations = await openConversations([
      call('create_screen', { name: 'Momentum leaders', market: 'US', definition: DEFINITION, source_screen_id: 4 }),
      call('create_screen', { name: 'Momentum leaders', market: 'US', definition: DEFINITION }),
      call('update_screen', { screen_id: 5, name: 'Momentum leaders (AI)', definition: DEFINITION }),
      { text: 'Done.' },
    ]);

    const events = await runOnce(conversations);

    expect(web.requests.map((request) => `${request.method} ${request.path}`)).toEqual([
      'GET /api/screens/4',
      'POST /api/screens',
      'POST /api/screens',
      'GET /api/screens/5',
      'PUT /api/screens/5',
    ]);
    const saved = { type: 'screen_saved', screen_id: 5, name: 'Momentum leaders (AI)', market: 'US', definition: SCREEN_DEFINITION };
    expect(eventsOfType(events, 'screen_saved')).toEqual([
      { ...saved, previous_definition: SOURCE_SCREEN.definition },
      { ...saved, previous_definition: null },
      { ...saved, previous_definition: SCREEN_DEFINITION },
    ]);
  });

  test('run_screen announces the funnel counts of the screen result for the condition card', async () => {
    const conversations = await openConversations([call('run_screen', { screen_id: 5 }), { text: 'Done.' }]);

    const events = await runOnce(conversations);

    expect(eventsOfType(events, 'screen_run_finished')).toEqual([
      {
        type: 'screen_run_finished',
        screen_id: 5,
        screen_result_id: 9,
        start_count: 500,
        after_filters_count: 300,
        after_indicator_conditions_count: 120,
        result_count: 120,
      },
    ]);
  });

  test('read_screen_result gives the summary and the first 50 rows, and reads the next page', async () => {
    const conversations = await openConversations([
      call('read_screen_result', { screen_result_id: 9 }),
      call('read_screen_result', { screen_result_id: 9, offset: 50 }),
      call('read_screen_result', { screen_result_id: 9, offset: 100 }),
      { text: 'Done.' },
    ]);

    await runOnce(conversations);

    const [first, second, last] = readToolResults() as Record<string, unknown>[];
    expect(first).toEqual({
      id: 9,
      screen_id: 5,
      market: 'US',
      summary: SCREEN_SUMMARY,
      definition: { start: 'quarter_universe' },
      offset: 0,
      rows: Array.from({ length: 50 }, (_unused, index) => screenRow(index + 1)),
      next_offset: 50,
    });
    expect((second?.rows as unknown[])[0]).toEqual(screenRow(51));
    expect(second?.next_offset).toBe(100);
    expect((last?.rows as unknown[]).length).toBe(20);
    expect(last?.next_offset).toBeNull();
  });

  test.each([
    ['create_screen', { name: 'Momentum leaders', market: 'US', definition: {} }],
    ['update_screen', { screen_id: 5, name: 'Momentum leaders (AI)', definition: {} }],
    ['run_screen', { screen_id: 5 }],
  ])('%s gives the problem list of a 422 to the model, and the model tries again', async (toolName, toolArguments) => {
    const problems = {
      problems: [{ location: ['definition', 'indicator_conditions', 0, 'operator'], message: "Use one of '<', '<=', '>', '>='." }],
    };
    web.screenAnswers.push({ status: 422, body: problems });
    const conversations = await openConversations([call(toolName, toolArguments), call(toolName, toolArguments), { text: 'Done.' }]);

    const events = await runOnce(conversations);

    const results = readToolResults();
    expect(results[0]).toBe(`Port 8001 answered 422: ${JSON.stringify(problems)}`);
    expect(eventsOfType(events, 'tool_step').map((event) => event.status)).toEqual([
      'running',
      'failed',
      'running',
      'succeeded',
    ]);
    // Only the second call saved: one card, or one count.
    expect([...eventsOfType(events, 'screen_saved'), ...eventsOfType(events, 'screen_run_finished')]).toHaveLength(1);
  });

  test('update_screen gives the 403 of a screen that it cannot change to the model', async () => {
    const refused = { detail: 'The AI assistant cannot change screen 5.' };
    web.screenAnswers.push({ status: 403, body: refused });
    const conversations = await openConversations([
      call('update_screen', { screen_id: 5, name: 'Value', definition: {} }),
      { text: 'Done.' },
    ]);

    await runOnce(conversations);

    expect(readToolResults()).toEqual([`Port 8001 answered 403: ${JSON.stringify(refused)}`]);
  });
});
