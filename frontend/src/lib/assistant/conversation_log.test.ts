import { describe, expect, it } from 'vite-plus/test';
import {
  addServerMessage,
  addUserMessage,
  describeToolStep,
  EMPTY_LOG,
  readConversationLog,
  type ConversationLog,
} from './conversation_log';

const NOW = '2026-01-02T03:04:05Z';

function toolStep(fields: Partial<{ status: 'running' | 'succeeded' | 'failed'; backtest_id: number | null; backtest_status: string | null; tool_name: string }>) {
  return {
    type: 'tool_step' as const,
    tool_call_id: 'call-1',
    tool_name: fields.tool_name ?? 'run_backtest',
    status: fields.status ?? 'running',
    backtest_id: fields.backtest_id ?? null,
    backtest_status: fields.backtest_status ?? null,
  };
}

describe('the conversation log', () => {
  it('shows the saved messages with the model and the credential name of each AI assistant message', () => {
    const log = readConversationLog(
      [
        { role: 'user', text: 'Hi.', provider: null, model: null, credential_name: null },
        { role: 'assistant', text: 'Hello.', provider: 'openai', model: 'gpt-a', credential_name: 'Work key' },
      ],
      NOW,
    );

    expect(log.items).toEqual([
      { kind: 'message', id: 0, sentAtUtc: NOW, role: 'user', text: 'Hi.', model: null, credentialName: null, streaming: false },
      { kind: 'message', id: 1, sentAtUtc: NOW, role: 'assistant', text: 'Hello.', model: 'gpt-a', credentialName: 'Work key', streaming: false },
    ]);
    expect(log.isRunning).toBe(false);
  });

  it('streams the answer into one message and ends it with the model and the credential name', () => {
    let log: ConversationLog = addUserMessage(EMPTY_LOG, 'Hi.', NOW);
    log = addServerMessage(log, { type: 'run_state', state: 'running' }, NOW);
    log = addServerMessage(log, { type: 'message_delta', text: 'Hel' }, NOW);
    log = addServerMessage(log, { type: 'message_delta', text: 'lo' }, NOW);

    expect(log.isRunning).toBe(true);
    expect(log.items.at(-1)).toMatchObject({ role: 'assistant', text: 'Hello', streaming: true });

    log = addServerMessage(
      log,
      { type: 'message_end', text: 'Hello.', provider: 'openai', model: 'gpt-b', credential_name: 'Home key' },
      NOW,
    );
    log = addServerMessage(log, { type: 'run_state', state: 'settled' }, NOW);

    expect(log.items).toHaveLength(2);
    expect(log.items.at(-1)).toMatchObject({
      role: 'assistant',
      text: 'Hello.',
      model: 'gpt-b',
      credentialName: 'Home key',
      streaming: false,
    });
    expect(log.isRunning).toBe(false);
  });

  it('keeps one line for each tool call and updates it', () => {
    let log = addServerMessage(EMPTY_LOG, toolStep({ backtest_id: 42, backtest_status: 'queued' }), NOW);
    log = addServerMessage(log, toolStep({ backtest_id: 42, backtest_status: 'running' }), NOW);

    expect(log.items).toHaveLength(1);
    expect(log.items[0]).toMatchObject({ kind: 'tool_step', backtestId: 42, backtestStatus: 'running' });
  });

  it('starts a new AI assistant message after a tool step', () => {
    let log = addServerMessage(EMPTY_LOG, { type: 'message_delta', text: 'First.' }, NOW);
    log = addServerMessage(log, toolStep({ tool_name: 'read_strategy' }), NOW);
    log = addServerMessage(log, { type: 'message_delta', text: 'Second.' }, NOW);

    expect(log.items.map((item) => item.kind)).toEqual(['message', 'tool_step', 'message']);
  });

  it('adds a diff card for a saved strategy version and a metric card for a finished backtest', () => {
    let log = addServerMessage(
      EMPTY_LOG,
      { type: 'strategy_version_saved', strategy_id: 3, strategy_version_id: 9, version_number: 4 },
      NOW,
    );
    log = addServerMessage(log, { type: 'backtest_finished', backtest_id: 42 }, NOW);

    expect(log.items).toEqual([
      { kind: 'diff', id: 0, sentAtUtc: NOW, strategyId: 3, versionNumber: 4 },
      { kind: 'metrics', id: 1, sentAtUtc: NOW, backtestId: 42 },
    ]);
  });

  it('adds a condition card for each saved screen; a run gives its funnel counts to the last card of that screen', () => {
    const saved = { type: 'screen_saved' as const, screen_id: 5, name: 'Momentum (AI)', market: 'US' };
    let log = addServerMessage(EMPTY_LOG, { ...saved, definition: { start: 'watchlist' }, previous_definition: null }, NOW);
    log = addServerMessage(log, { ...saved, definition: { start: 'quarter_universe' }, previous_definition: { start: 'watchlist' } }, NOW);
    const counts = { start_count: 500, after_filters_count: 300, after_indicator_conditions_count: 40, result_count: 20 };
    log = addServerMessage(log, { type: 'screen_run_finished', screen_id: 5, screen_result_id: 9, ...counts }, NOW);
    log = addServerMessage(log, { type: 'screen_run_finished', screen_id: 6, screen_result_id: 10, ...counts }, NOW);

    expect(log.items).toEqual([
      {
        kind: 'screen',
        id: 0,
        sentAtUtc: NOW,
        screenId: 5,
        name: 'Momentum (AI)',
        market: 'US',
        definition: { start: 'watchlist' },
        previousDefinition: null,
        counts: null,
      },
      {
        kind: 'screen',
        id: 1,
        sentAtUtc: NOW,
        screenId: 5,
        name: 'Momentum (AI)',
        market: 'US',
        definition: { start: 'quarter_universe' },
        previousDefinition: { start: 'watchlist' },
        counts,
      },
    ]);
  });
});

describe('the text of a tool step', () => {
  it('names the backtest and its state for run_backtest', () => {
    expect(describeToolStep({ toolName: 'run_backtest', status: 'running', backtestId: 42, backtestStatus: 'running' })).toEqual({
      label: 'Backtest #42 running',
      kind: 'in-progress',
    });
    expect(describeToolStep({ toolName: 'run_backtest', status: 'succeeded', backtestId: 42, backtestStatus: 'finished' })).toEqual({
      label: 'Backtest #42 finished',
      kind: 'success',
    });
    expect(describeToolStep({ toolName: 'run_backtest', status: 'failed', backtestId: 42, backtestStatus: 'timed_out' })).toEqual({
      label: 'Backtest #42 timed out',
      kind: 'error',
    });
  });

  it('names the tool and the tool state for the other tools', () => {
    expect(describeToolStep({ toolName: 'save_strategy_version', status: 'succeeded', backtestId: null, backtestStatus: null })).toEqual({
      label: 'Save strategy version succeeded',
      kind: 'success',
    });
    expect(describeToolStep({ toolName: 'read_backtest', status: 'failed', backtestId: null, backtestStatus: null })).toEqual({
      label: 'Read backtest failed',
      kind: 'error',
    });
  });
});
