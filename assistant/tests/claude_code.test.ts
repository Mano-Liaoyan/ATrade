// The Claude Code runner (docs/architecture/assistant.md 25.7.5, ADR 0010). The Claude Agent SDK is a fake query
// (fake_claude_code.ts): no `claude` process and no model request.
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { defineTool } from '@earendil-works/pi-coding-agent';
import { Type } from 'typebox';
import { afterEach, beforeEach, describe, expect, test } from 'vite-plus/test';
import { ClaudeCode, CLAUDE_LOGIN_COMMAND, lowerThinkingLevel } from '../src/claude_code.ts';
import { Conversations, type RunEvent } from '../src/conversations.ts';
import type { ModelSelection, ThinkingLevel } from '../src/model_selection.ts';
import {
  createFakeClaudeCode,
  LOGGED_OUT_ACCOUNT,
  successResult,
  textAnswer,
  type FakeClaudeCode,
  type FakeScript,
} from './fake_claude_code.ts';

const SELECTION: ModelSelection = { provider: 'claude-code', model: 'opus', credentialId: 'claude-code' };
const PI_SELECTION: ModelSelection = { provider: 'fake', model: 'fake-model', credentialId: 'fake-key-1' };
const SYSTEM_PROMPT = 'Answer in short sentences.';

const listStrategies = defineTool({
  name: 'list_strategies',
  label: 'List strategies',
  description: 'Lists the strategies.',
  parameters: Type.Object({ limit: Type.Integer({ minimum: 1 }) }),
  execute: (_id, params) =>
    Promise.resolve({ content: [{ type: 'text', text: `limit ${String(params.limit)}` }], details: {} }),
});

let workDir: string;
let removedSessions: string[];
/** The Claude Code sessions with a file. The fake query does not write files. */
let sessionFiles: Set<string>;

beforeEach(() => {
  workDir = mkdtempSync(path.join(tmpdir(), 'atrade-claude-code-'));
  removedSessions = [];
  sessionFiles = new Set();
});

afterEach(() => {
  rmSync(workDir, { recursive: true, force: true });
});

function openClaudeCode(script: FakeScript): { claudeCode: ClaudeCode; fake: FakeClaudeCode; conversations: Conversations } {
  const fake = createFakeClaudeCode(script);
  const claudeCode = new ClaudeCode({
    workDir: path.join(workDir, 'claude-code'),
    runQuery: fake.runQuery,
    removeSession: (sessionId) => {
      removedSessions.push(sessionId);
      return Promise.resolve();
    },
    hasSession: (sessionId) => Promise.resolve(sessionFiles.has(sessionId)),
  });
  const conversations = new Conversations({
    piDir: workDir,
    openModel: () => Promise.reject(new Error('This test has no pi model.')),
    createTools: () => [listStrategies],
    claudeCode,
  });
  return { claudeCode, fake, conversations };
}

async function runOnce(
  conversations: Conversations,
  text: string,
  selection: ModelSelection = SELECTION,
  thinkingLevel: ThinkingLevel = 'high',
): Promise<RunEvent[]> {
  const events: RunEvent[] = [];
  await conversations.run('7', { text, selection, thinkingLevel, systemPrompt: SYSTEM_PROMPT }, (event) => events.push(event));
  return events;
}

describe('the Claude Code status', () => {
  test('a Claude login gives the models with their thinking levels and a ready credential named by the email', async () => {
    const { claudeCode } = openClaudeCode({});

    const provider = await claudeCode.providerSummary();
    const credential = await claudeCode.credentialSummary();

    expect(provider).toEqual({
      id: 'claude-code',
      name: 'Claude Code',
      login_methods: [],
      models: [
        { id: 'opus', name: 'Opus', thinking_levels: ['off', 'low', 'medium', 'high', 'max'], reads_images: true },
        { id: 'haiku', name: 'Haiku', thinking_levels: ['off'], reads_images: true },
      ],
    });
    expect(credential).toMatchObject({ id: 'claude-code', name: 'trader@example.test', type: 'claude_code', state: 'ready' });
  });

  test('without a login, the provider has no models and the credential gives the login command', async () => {
    const { claudeCode } = openClaudeCode({ account: LOGGED_OUT_ACCOUNT });

    expect((await claudeCode.providerSummary()).models).toEqual([]);
    const credential = await claudeCode.credentialSummary();
    expect(credential.state).toBe('failed');
    expect(credential.state_message).toContain(CLAUDE_LOGIN_COMMAND);
  });

  test('a binary that does not start gives the reason', async () => {
    const { claudeCode } = openClaudeCode({ startError: 'spawn claude ENOENT' });

    const credential = await claudeCode.credentialSummary();

    expect(credential.state).toBe('failed');
    expect(credential.state_message).toContain('spawn claude ENOENT');
  });

  test('the probe sends no message and loads no settings', async () => {
    const { claudeCode, fake } = openClaudeCode({});

    await claudeCode.credentialSummary();
    await claudeCode.providerSummary();

    expect(fake.calls).toHaveLength(1);
    expect(fake.calls[0]?.options).toMatchObject({ settingSources: [], persistSession: false });
  });

  test('a requested thinking level goes down to a level of the model', () => {
    expect(lowerThinkingLevel('xhigh', ['off', 'low', 'medium', 'high', 'max'])).toBe('high');
    expect(lowerThinkingLevel('minimal', ['off', 'low'])).toBe('off');
    expect(lowerThinkingLevel('max', ['off'])).toBe('off');
  });
});

describe('a Claude Code run', () => {
  test('streams the answer and ends it with the selected model, the email, and the thinking level', async () => {
    const { conversations } = openClaudeCode({ runs: [[...textAnswer('m1', ['Hello ', 'there.']), successResult()]] });

    const events = await runOnce(conversations, 'Hi.');

    expect(events).toEqual([
      { type: 'text_delta', delta: 'Hello ' },
      { type: 'text_delta', delta: 'there.' },
      {
        type: 'message_end',
        text: 'Hello there.',
        provider: 'claude-code',
        model: 'opus',
        credential_name: 'trader@example.test',
        thinking_level: 'high',
      },
    ]);
  });

  test('runs only the ATrade tools and the 2 web tools, loads no settings, and uses no API key', async () => {
    const original = process.env.ANTHROPIC_API_KEY;
    process.env.ANTHROPIC_API_KEY = 'sk-ant-test-not-real';
    try {
      const { conversations, fake } = openClaudeCode({ runs: [[successResult()]] });

      await runOnce(conversations, 'Hi.');

      const options = fake.calls.at(-1)?.options;
      expect(options).toMatchObject({
        model: 'opus',
        systemPrompt: SYSTEM_PROMPT,
        settingSources: [],
        strictMcpConfig: true,
        permissionMode: 'dontAsk',
        tools: ['WebSearch', 'WebFetch'],
        allowedTools: ['WebSearch', 'WebFetch', 'mcp__atrade__*'],
        thinking: { type: 'adaptive' },
        effort: 'high',
      });
      expect(Object.keys(options?.mcpServers ?? {})).toEqual(['atrade']);
      expect(options?.env?.ANTHROPIC_API_KEY).toBeUndefined();
    } finally {
      if (original === undefined) {
        delete process.env.ANTHROPIC_API_KEY;
      } else {
        process.env.ANTHROPIC_API_KEY = original;
      }
    }
  });

  test('the thinking level "off" turns the thinking off', async () => {
    const { conversations, fake } = openClaudeCode({ runs: [[successResult()]] });

    await runOnce(conversations, 'Hi.', SELECTION, 'off');

    expect(fake.calls.at(-1)?.options.thinking).toEqual({ type: 'disabled' });
    expect(fake.calls.at(-1)?.options.effort).toBeUndefined();
  });

  test('an ATrade tool runs through the MCP server, with the TypeBox conversion, and sends tool steps', async () => {
    const { conversations, fake } = openClaudeCode({
      runs: [[{ callTool: 'list_strategies', arguments: { limit: '2' } }, successResult()]],
    });

    const events = await runOnce(conversations, 'List them.');

    expect(fake.toolResults).toEqual([{ content: [{ type: 'text', text: 'limit 2' }], isError: false }]);
    expect(events.map((event) => (event.type === 'tool_step' ? `${event.tool_name} ${event.status}` : event.type))).toEqual([
      'list_strategies running',
      'list_strategies succeeded',
    ]);
  });

  test('refuses arguments that do not match the tool parameters', async () => {
    const { conversations, fake } = openClaudeCode({
      runs: [[{ callTool: 'list_strategies', arguments: { limit: 0 } }, successResult()]],
    });

    const events = await runOnce(conversations, 'List them.');

    expect(fake.toolResults[0]).toMatchObject({ isError: true });
    expect(events.at(-1)).toMatchObject({ type: 'tool_step', status: 'failed' });
  });

  test('a built-in web tool call shows as a tool step with the name of the web page', async () => {
    const common = { parent_tool_use_id: null, uuid: 'u', session_id: 's' };
    const { conversations } = openClaudeCode({
      runs: [
        [
          {
            type: 'assistant',
            message: { id: 'm1', model: 'x', content: [{ type: 'tool_use', id: 'tool-1', name: 'WebSearch', input: {} }] },
            ...common,
          },
          {
            type: 'user',
            message: { role: 'user', content: [{ type: 'tool_result', tool_use_id: 'tool-1', content: 'found' }] },
            ...common,
          },
          successResult(),
        ] as never,
      ],
    });

    const events = await runOnce(conversations, 'Search.');

    expect(events).toMatchObject([
      { type: 'tool_step', tool_call_id: 'tool-1', tool_name: 'web_search', status: 'running' },
      { type: 'tool_step', tool_call_id: 'tool-1', tool_name: 'web_search', status: 'succeeded' },
    ]);
  });

  test('a lost login gives one error event with the login command', async () => {
    const common = { parent_tool_use_id: null, uuid: 'u', session_id: 's' };
    const { conversations } = openClaudeCode({
      runs: [
        [
          {
            type: 'assistant',
            message: { id: 'm1', model: 'x', content: [{ type: 'text', text: 'Not logged in' }] },
            error: 'authentication_failed',
            ...common,
          },
          { type: 'result', subtype: 'success', is_error: true, result: 'Not logged in' },
        ] as never,
      ],
    });

    const events = await runOnce(conversations, 'Hi.');

    expect(events).toEqual([{ type: 'error', message: expect.stringContaining(CLAUDE_LOGIN_COMMAND) as string }]);
  });

  test('without a login, the run sends no message to Claude Code', async () => {
    const { conversations, fake } = openClaudeCode({ account: LOGGED_OUT_ACCOUNT, runs: [[successResult()]] });

    const events = await runOnce(conversations, 'Hi.');

    expect(events).toEqual([{ type: 'error', message: expect.stringContaining(CLAUDE_LOGIN_COMMAND) as string }]);
    expect(fake.calls.filter((call) => call.options.includePartialMessages === true)).toEqual([]);
  });

  test('abort stops the run without an error event', async () => {
    const { conversations } = openClaudeCode({ runs: [[...textAnswer('m1', ['Part']), { waitForAbort: true }]] });

    const run = runOnce(conversations, 'Hi.');
    await new Promise((resolve) => setTimeout(resolve, 50));
    await conversations.abort('7');
    const events = await run;

    expect(events.map((event) => event.type)).toEqual(['text_delta', 'message_end']);
  });
});

describe('a Claude Code conversation', () => {
  test('keeps the message texts, and the next run resumes the same Claude Code session', async () => {
    const { conversations, fake } = openClaudeCode({
      runs: [
        [...textAnswer('m1', ['First answer.']), successResult()],
        [...textAnswer('m2', ['Second answer.']), successResult()],
      ],
    });

    await runOnce(conversations, 'First question.');
    sessionFiles.add(String(fake.calls.at(-1)?.options.sessionId));
    await runOnce(conversations, 'Second question.');

    const [first, second] = fake.calls.filter((call) => call.options.includePartialMessages === true);
    expect(first?.options.sessionId).toEqual(expect.any(String));
    expect(first?.options.resume).toBeUndefined();
    expect(second?.options.resume).toBe(first?.options.sessionId);
    expect(conversations.readMessages('7')).toEqual([
      { role: 'user', text: 'First question.', provider: null, model: null, credential_name: null, thinking_level: null },
      {
        role: 'assistant',
        text: 'First answer.',
        provider: 'claude-code',
        model: 'opus',
        credential_name: 'trader@example.test',
        thinking_level: 'high',
      },
      { role: 'user', text: 'Second question.', provider: null, model: null, credential_name: null, thinking_level: null },
      {
        role: 'assistant',
        text: 'Second answer.',
        provider: 'claude-code',
        model: 'opus',
        credential_name: 'trader@example.test',
        thinking_level: 'high',
      },
    ]);
  });

  test('a run after a first run without a session file starts the session again with the same ID', async () => {
    const { conversations, fake } = openClaudeCode({ runs: [[], [successResult()]] });

    await runOnce(conversations, 'First question.');
    await runOnce(conversations, 'Second question.');

    const [first, second] = fake.calls.filter((call) => call.options.includePartialMessages === true);
    expect(second?.options.resume).toBeUndefined();
    expect(second?.options.sessionId).toBe(first?.options.sessionId);
  });

  test('refuses a pi model in a Claude Code conversation', async () => {
    const { conversations } = openClaudeCode({ runs: [[...textAnswer('m1', ['Answer.']), successResult()]] });
    await runOnce(conversations, 'Question.');

    const events = await runOnce(conversations, 'Next.', PI_SELECTION);

    expect(events).toEqual([{ type: 'error', message: expect.stringContaining('runs in Claude Code') as string }]);
  });

  test('the title comes from one Claude Code call without tools and without a session', async () => {
    const { conversations, fake } = openClaudeCode({
      runs: [
        [...textAnswer('m1', ['Answer.']), successResult()],
        [{ type: 'result', subtype: 'success', is_error: false, result: 'Moving average test' } as never],
      ],
    });
    await runOnce(conversations, 'Question.');

    const title = await conversations.generateTitle('7', SELECTION);

    expect(title).toBe('Moving average test');
    expect(fake.calls.at(-1)?.options).toMatchObject({ tools: [], allowedTools: [], persistSession: false, maxTurns: 1 });
  });

  test('delete removes the Claude Code session and the JSONL file', async () => {
    const { conversations, fake } = openClaudeCode({ runs: [[...textAnswer('m1', ['Answer.']), successResult()]] });
    await runOnce(conversations, 'Question.');

    await conversations.delete('7');

    expect(removedSessions).toEqual([fake.calls.find((call) => call.options.sessionId !== undefined)?.options.sessionId]);
    expect(conversations.readMessages('7')).toEqual([]);
  });
});
