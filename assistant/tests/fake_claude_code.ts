// A fake query of the Claude Agent SDK for the Claude Code tests (docs/architecture/assistant.md 25.7.5).
// No `claude` process and no model request. Each query gives the scripted SDK messages and keeps its options. A
// script step can call an ATrade tool through the MCP server of the run, as Claude Code does.
import type { McpSdkServerConfigWithInstance, Options, Query, SDKMessage } from '@anthropic-ai/claude-agent-sdk';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';
import type { RunQuery } from '../src/claude_code.ts';

export type FakeStep =
  | SDKMessage
  | { callTool: string; arguments: Record<string, unknown> }
  | { waitForAbort: true };

export interface FakeQueryCall {
  prompt: unknown;
  options: Options;
}

export interface FakeClaudeCode {
  runQuery: RunQuery;
  calls: FakeQueryCall[];
  /** The tool results that the fake Claude Code got from the MCP server. */
  toolResults: unknown[];
}

export const LOGGED_IN_ACCOUNT = { email: 'trader@example.test', subscriptionType: 'max', apiProvider: 'firstParty' as const };
export const LOGGED_OUT_ACCOUNT = { tokenSource: 'none', apiProvider: 'firstParty' as const };
export const FAKE_MODELS = [
  { value: 'opus', displayName: 'Opus', description: '', supportedEffortLevels: ['low', 'medium', 'high', 'max'] },
  { value: 'haiku', displayName: 'Haiku', description: '' },
];

async function callTool(options: Options, name: string, args: Record<string, unknown>): Promise<unknown> {
  const server = options.mcpServers?.atrade as McpSdkServerConfigWithInstance;
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  await server.instance.connect(serverTransport);
  const client = new Client({ name: 'fake-claude-code', version: '1.0.0' });
  await client.connect(clientTransport);
  try {
    return await client.callTool({ name, arguments: args });
  } finally {
    await client.close();
  }
}

function waitForAbort(options: Options): Promise<never> {
  return new Promise((_resolve, reject) => {
    options.abortController?.signal.addEventListener('abort', () => {
      reject(new Error('The operation was aborted.'));
    });
  });
}

export interface FakeScript {
  /** The steps of each run, in order of the runs. */
  runs?: FakeStep[][];
  account?: Record<string, unknown>;
  /** The probe fails with this error. */
  startError?: string;
}

export function createFakeClaudeCode(script: FakeScript): FakeClaudeCode {
  const calls: FakeQueryCall[] = [];
  const toolResults: unknown[] = [];
  const runs = [...(script.runs ?? [])];
  const runQuery = ((params: { prompt: unknown; options?: Options }) => {
    const options = params.options ?? {};
    calls.push({ prompt: params.prompt, options });
    const steps = options.includePartialMessages === true || typeof params.prompt === 'string' ? (runs.shift() ?? []) : [];
    async function* messages(): AsyncGenerator<SDKMessage> {
      for (const step of steps) {
        if ('callTool' in step) {
          toolResults.push(await callTool(options, step.callTool, step.arguments));
        } else if ('waitForAbort' in step) {
          await waitForAbort(options);
        } else {
          yield step;
        }
      }
    }
    return Object.assign(messages(), {
      initializationResult: () =>
        script.startError === undefined
          ? Promise.resolve({ account: script.account ?? LOGGED_IN_ACCOUNT, models: FAKE_MODELS })
          : Promise.reject(new Error(script.startError)),
      close: () => undefined,
    }) as unknown as Query;
  }) as RunQuery;
  return { runQuery, calls, toolResults };
}

/** The stream events and the assistant message of one answer with text, as Claude Code sends them. */
export function textAnswer(id: string, parts: string[]): SDKMessage[] {
  const common = { parent_tool_use_id: null, uuid: id, session_id: 'session' };
  return [
    { type: 'stream_event', event: { type: 'message_start', message: { id, model: 'claude-opus' } }, ...common },
    ...parts.map((text) => ({
      type: 'stream_event',
      event: { type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text } },
      ...common,
    })),
    { type: 'stream_event', event: { type: 'message_stop' }, ...common },
    {
      type: 'assistant',
      message: { id, model: 'claude-opus', content: [{ type: 'text', text: parts.join('') }] },
      ...common,
    },
  ] as unknown as SDKMessage[];
}

export function successResult(): SDKMessage {
  return { type: 'result', subtype: 'success', is_error: false, result: '' } as unknown as SDKMessage;
}
