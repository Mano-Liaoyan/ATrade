// The Claude Code runner of the AI assistant (docs/architecture/assistant.md 25.7.5, ADR 0010).
// A run goes through the Claude Agent SDK. The SDK starts the official, unmodified `claude` binary of its platform
// package. The binary uses the Claude login of the container: the user runs `claude auth login` in the container one
// time, and Claude Code keeps the login in HOME/.claude (the volume atrade-assistant-pi). ATrade never reads, stores, or
// sends that login. Anthropic permits a Claude subscription login only in Claude Code and other Anthropic apps.
//
// The isolation of each run:
// - The tools are the ATrade tools (an MCP server in this process) and the built-in tools WebSearch and WebFetch.
//   permissionMode "dontAsk" refuses each other tool.
// - No settings file, no CLAUDE.md, no hook, and no plugin from the file system (settingSources: []). No other MCP
//   server (strictMcpConfig).
// - The working directory is an empty directory in the volume.
// - No API key in the environment, so the run always uses the Claude login.
import { randomUUID } from 'node:crypto';
import { mkdirSync } from 'node:fs';
import {
  deleteSession,
  getSessionInfo,
  query,
  type AccountInfo,
  type EffortLevel,
  type McpSdkServerConfigWithInstance,
  type ModelInfo,
  type Options,
  type SDKMessage,
  type SDKUserMessage,
} from '@anthropic-ai/claude-agent-sdk';
import type { ToolDefinition } from '@earendil-works/pi-coding-agent';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { CallToolRequestSchema, ListToolsRequestSchema, type CallToolResult } from '@modelcontextprotocol/sdk/types.js';
import { Value } from 'typebox/value';
import type { CompleteText } from './conversation_title.ts';
import type { PromptImage, RunEvent } from './conversations.ts';
import type { CredentialSummary } from './credential_file.ts';
import { THINKING_LEVELS, type ThinkingLevel } from './model_selection.ts';
import type { ProviderSummary } from './providers.ts';
import { endToolEvents, startToolEvents, updateToolEvents, type ToolCall } from './tool_events.ts';
import { errorResult, type ToolResult } from './tool_results.ts';

export const CLAUDE_CODE_PROVIDER = 'claude-code';
/** The one credential of Claude Code: the Claude login of the container. It is not in the credential file. */
export const CLAUDE_CODE_CREDENTIAL_ID = 'claude-code';
/** The command that logs in Claude Code in the container. The user runs it in the repository on the server. */
export const CLAUDE_LOGIN_COMMAND = 'docker compose -f deploy/compose.yaml exec assistant claude auth login';

const TOOL_SERVER = 'atrade';
const BUILT_IN_TOOLS = ['WebSearch', 'WebFetch'];
/** The tool names that the web page shows for the built-in web tools: the names of the pi web tools (25.4.5). */
const BUILT_IN_TOOL_NAMES: Record<string, string> = { WebSearch: 'web_search', WebFetch: 'fetch_content' };
/** The environment variables that make Claude Code use an API key or another provider instead of the Claude login. */
const REMOVED_ENVIRONMENT = [
  'ANTHROPIC_API_KEY',
  'ANTHROPIC_AUTH_TOKEN',
  'ANTHROPIC_BASE_URL',
  'CLAUDE_CODE_USE_BEDROCK',
  'CLAUDE_CODE_USE_VERTEX',
  'CLAUDE_CODE_USE_FOUNDRY',
];
/** The status probe starts a `claude` process. The providers list and the credentials list share one probe. */
const STATUS_LIFETIME_MS = 10_000;
const STATUS_TIMEOUT_MS = 30_000;
const EFFORT_LEVELS: readonly string[] = ['low', 'medium', 'high', 'xhigh', 'max'];

export type RunQuery = typeof query;

export interface ClaudeCodeStatus {
  account: AccountInfo | null;
  models: ModelInfo[];
  /** The reason when the probe failed, for example no `claude` binary. */
  error: string | null;
}

export interface ClaudeCodeOptions {
  /** The empty working directory of the runs. The Claude Code sessions of the conversations belong to it. */
  workDir: string;
  /** Tests give a fake query. Default: the query of the SDK. */
  runQuery?: RunQuery;
  /** Default: deleteSession of the SDK. */
  removeSession?: (sessionId: string, workDir: string) => Promise<void>;
  /** Default: getSessionInfo of the SDK. */
  hasSession?: (sessionId: string, workDir: string) => Promise<boolean>;
}

export interface ClaudeCodeRunRequest {
  text: string;
  images: PromptImage[];
  model: string;
  thinkingLevel: ThinkingLevel;
  systemPrompt: string;
  tools: ToolDefinition[];
  /** The Claude Code session of the conversation. */
  sessionId: string;
  /** True: the conversation has the session, and the run resumes it when Claude Code has its file. A first run that
   * stopped before Claude Code wrote the file starts the session again with the same ID. */
  resume: boolean;
  abortController: AbortController;
}

function readErrorText(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

export function isLoggedIn(account: AccountInfo | null): boolean {
  if (account === null) {
    return false;
  }
  // Without a login, Claude Code gives tokenSource "none". With a Claude login, it gives no tokenSource.
  return account.tokenSource !== 'none' || (account.apiKeySource ?? 'none') !== 'none';
}

/** The thinking levels of a model: "off" and its effort levels, in the order of THINKING_LEVELS. */
export function listClaudeThinkingLevels(model: ModelInfo): ThinkingLevel[] {
  const efforts: readonly string[] = model.supportedEffortLevels ?? [];
  return THINKING_LEVELS.filter((level) => level === 'off' || efforts.includes(level));
}

/** The requested level, or the next lower level of the model, as pi does. */
export function lowerThinkingLevel(requested: ThinkingLevel, levels: ThinkingLevel[]): ThinkingLevel {
  const limit = THINKING_LEVELS.indexOf(requested);
  return levels.filter((level) => THINKING_LEVELS.indexOf(level) <= limit).at(-1) ?? 'off';
}

function thinkingOptions(level: ThinkingLevel): Pick<Options, 'thinking' | 'effort'> {
  if (level === 'off' || !EFFORT_LEVELS.includes(level)) {
    return { thinking: { type: 'disabled' } };
  }
  return { thinking: { type: 'adaptive' }, effort: level as EffortLevel };
}

function createEnvironment(): Record<string, string | undefined> {
  const environment = Object.fromEntries(
    Object.entries(process.env).filter(([name]) => !REMOVED_ENVIRONMENT.includes(name)),
  );
  return {
    ...environment,
    // The image is read-only. The SDK version in package.json gives the binary version.
    DISABLE_AUTOUPDATER: '1',
    CLAUDE_CODE_DISABLE_AUTO_MEMORY: '1',
    CLAUDE_AGENT_SDK_CLIENT_APP: 'atrade',
  };
}

/** A prompt that sends no message and ends when the signal aborts. The status probe needs only the initialization. */
function waitForAbort(signal: AbortSignal): AsyncIterable<SDKUserMessage> {
  return {
    [Symbol.asyncIterator]: () => ({
      next: () =>
        new Promise<IteratorResult<SDKUserMessage>>((resolve) => {
          signal.addEventListener(
            'abort',
            () => {
              resolve({ done: true, value: undefined });
            },
            { once: true },
          );
        }),
    }),
  };
}

/** A prompt with one user message. */
function sendOnce(message: SDKUserMessage): AsyncIterable<SDKUserMessage> {
  let sent = false;
  return {
    [Symbol.asyncIterator]: () => ({
      next: () => {
        const result: IteratorResult<SDKUserMessage> = sent ? { done: true, value: undefined } : { done: false, value: message };
        sent = true;
        return Promise.resolve(result);
      },
    }),
  };
}

function toUserMessage(text: string, images: PromptImage[]): SDKUserMessage {
  return {
    type: 'user',
    parent_tool_use_id: null,
    message: {
      role: 'user',
      content: [
        { type: 'text', text },
        ...images.map((image) => ({
          type: 'image' as const,
          source: {
            type: 'base64' as const,
            media_type: image.mimeType as 'image/png' | 'image/jpeg' | 'image/gif' | 'image/webp',
            // eslint-disable-next-line @typescript-eslint/naming-convention -- readability-exception: the Anthropic API field.
            data: image.data,
          },
        })),
      ],
    },
  };
}

function toMcpResult(result: ToolResult): CallToolResult {
  return {
    content: result.content.map((part) =>
      part.type === 'text'
        ? { type: 'text' as const, text: part.text }
        : // eslint-disable-next-line @typescript-eslint/naming-convention -- readability-exception: the MCP field.
          { type: 'image' as const, data: part.data, mimeType: part.mimeType },
    ),
    isError: result.isError === true,
  };
}

/** Runs one ATrade tool for Claude Code. The arguments go through the same TypeBox conversion and check as in pi. */
async function callTool(
  tools: ToolDefinition[],
  name: string,
  args: Record<string, unknown>,
  emit: (event: RunEvent) => void,
  signal: AbortSignal,
): Promise<CallToolResult> {
  const tool = tools.find((item) => item.name === name);
  if (tool === undefined) {
    return toMcpResult(errorResult(`${name} is not an ATrade assistant tool.`));
  }
  const call: ToolCall = { toolCallId: randomUUID(), toolName: name };
  startToolEvents(call).forEach(emit);
  const params: unknown = Value.Convert(tool.parameters, structuredClone(args));
  if (!Value.Check(tool.parameters, params)) {
    const problems = [...Value.Errors(tool.parameters, params)].map((problem) => `${problem.instancePath} ${problem.message}`);
    const result = errorResult(`The arguments of ${name} are not valid: ${problems.join('; ')}`);
    endToolEvents(call, result, true).forEach(emit);
    return toMcpResult(result);
  }
  try {
    const onUpdate = (partial: unknown) => {
      updateToolEvents(call, partial).forEach(emit);
    };
    // The ATrade tools do not read the extension context of pi (the fifth argument).
    const result = (await tool.execute(call.toolCallId, params, signal, onUpdate, undefined as never)) as ToolResult;
    endToolEvents(call, result, result.isError === true).forEach(emit);
    return toMcpResult(result);
  } catch (error) {
    const result = errorResult(readErrorText(error));
    endToolEvents(call, result, true).forEach(emit);
    return toMcpResult(result);
  }
}

/** The ATrade tools as an MCP server in this process. The tool schemas are the TypeBox schemas (JSON Schema). */
function createToolServer(
  tools: ToolDefinition[],
  emit: (event: RunEvent) => void,
  signal: AbortSignal,
): McpSdkServerConfigWithInstance {
  const server = new McpServer({ name: TOOL_SERVER, version: '1.0.0' }, { capabilities: { tools: {} } });
  server.server.setRequestHandler(ListToolsRequestSchema, () => ({
    tools: tools.map((tool) => ({
      name: tool.name,
      description: tool.description,
      inputSchema: tool.parameters as unknown as { type: 'object' },
    })),
  }));
  server.server.setRequestHandler(CallToolRequestSchema, (request) =>
    callTool(tools, request.params.name, request.params.arguments ?? {}, emit, signal),
  );
  return { type: 'sdk', name: TOOL_SERVER, instance: server };
}

interface RunLabels {
  credentialName: string;
  thinkingLevel: ThinkingLevel;
  /** The model ID of the selection, for example "opus". The browser selects the model of the last message again. */
  model: string;
}

interface ContentBlock {
  type: string;
  id?: string;
  name?: string;
  text?: string;
  tool_use_id?: string;
  is_error?: boolean;
}

/** Changes the SDK messages of one run into run events: the same events as a pi run (conversations.ts). */
class RunReader {
  private readonly emit: (event: RunEvent) => void;
  private readonly labels: RunLabels;
  private text = '';
  /** The messages that came as stream events. Their text is already in a message_end event. */
  private readonly streamedMessages = new Set<string>();
  /** The built-in tool calls that run: the tool use ID and the tool name of the web page. */
  private readonly builtInCalls = new Map<string, string>();
  failed = false;

  constructor(emit: (event: RunEvent) => void, labels: RunLabels) {
    this.emit = emit;
    this.labels = labels;
  }

  read(message: SDKMessage): void {
    switch (message.type) {
      case 'stream_event':
        if (message.parent_tool_use_id === null) {
          this.readStreamEvent(message.event as { type: string; message?: { id: string } });
        }
        break;
      case 'assistant':
        this.readAssistantMessage(message.message, message.error);
        break;
      case 'user':
        this.readToolResults(message.message.content);
        break;
      case 'result':
        if (message.is_error) {
          const reason = message.subtype === 'success' ? message.result : message.errors.join(' ');
          this.fail(reason === '' ? `Claude Code stopped: ${message.subtype}.` : reason);
        }
        break;
      default:
        break;
    }
  }

  private readStreamEvent(event: { type: string; message?: { id: string }; delta?: ContentBlock }): void {
    if (event.type === 'message_start' && event.message !== undefined) {
      this.streamedMessages.add(event.message.id);
      this.text = '';
    } else if (event.type === 'content_block_delta' && event.delta?.type === 'text_delta') {
      const delta = event.delta.text ?? '';
      this.text += delta;
      this.emit({ type: 'text_delta', delta });
    } else if (event.type === 'message_stop') {
      this.endMessage(this.text);
      this.text = '';
    }
  }

  private endMessage(text: string): void {
    if (text === '') {
      return;
    }
    this.emit({
      type: 'message_end',
      text,
      provider: CLAUDE_CODE_PROVIDER,
      model: this.labels.model,
      credential_name: this.labels.credentialName,
      thinking_level: this.labels.thinkingLevel,
    });
  }

  private readAssistantMessage(message: { id: string; content: ContentBlock[] }, error?: string): void {
    const text = message.content
      .filter((block) => block.type === 'text')
      .map((block) => block.text ?? '')
      .join('');
    if (error !== undefined) {
      this.fail(
        error === 'authentication_failed'
          ? `Claude Code is not logged in. Run this command on the server: ${CLAUDE_LOGIN_COMMAND}`
          : text === ''
            ? `Claude Code sent the error ${error}.`
            : text,
      );
      return;
    }
    // A message without stream events (for example a request that Claude Code sent again without streaming).
    if (!this.streamedMessages.has(message.id)) {
      this.endMessage(text);
    }
    for (const block of message.content) {
      const toolName = block.type === 'tool_use' ? BUILT_IN_TOOL_NAMES[block.name ?? ''] : undefined;
      if (toolName !== undefined && block.id !== undefined) {
        this.builtInCalls.set(block.id, toolName);
        startToolEvents({ toolCallId: block.id, toolName }).forEach(this.emit);
      }
    }
  }

  private readToolResults(content: unknown): void {
    if (!Array.isArray(content)) {
      return;
    }
    for (const block of content as ContentBlock[]) {
      const toolName = block.tool_use_id === undefined ? undefined : this.builtInCalls.get(block.tool_use_id);
      if (block.type === 'tool_result' && block.tool_use_id !== undefined && toolName !== undefined) {
        this.builtInCalls.delete(block.tool_use_id);
        endToolEvents({ toolCallId: block.tool_use_id, toolName }, {}, block.is_error === true).forEach(this.emit);
      }
    }
  }

  private fail(message: string): void {
    if (!this.failed) {
      this.failed = true;
      this.emit({ type: 'error', message });
    }
  }
}

export class ClaudeCode {
  private readonly workDir: string;
  private readonly runQuery: RunQuery;
  private readonly removeSession: (sessionId: string, workDir: string) => Promise<void>;
  private readonly hasSession: (sessionId: string, workDir: string) => Promise<boolean>;
  private status: { at: number; promise: Promise<ClaudeCodeStatus> } | null = null;

  constructor(options: ClaudeCodeOptions) {
    this.workDir = options.workDir;
    this.runQuery = options.runQuery ?? query;
    this.removeSession = options.removeSession ?? ((sessionId, dir) => deleteSession(sessionId, { dir }));
    this.hasSession =
      options.hasSession ?? (async (sessionId, dir) => (await getSessionInfo(sessionId, { dir })) !== undefined);
    mkdirSync(this.workDir, { recursive: true });
  }

  private baseOptions(): Options {
    return {
      cwd: this.workDir,
      env: createEnvironment(),
      settingSources: [],
      strictMcpConfig: true,
      permissionMode: 'dontAsk',
      tools: BUILT_IN_TOOLS,
      allowedTools: [...BUILT_IN_TOOLS, `mcp__${TOOL_SERVER}__*`],
    };
  }

  /** The login and the models of Claude Code. One probe serves the calls of STATUS_LIFETIME_MS. */
  readStatus(): Promise<ClaudeCodeStatus> {
    const now = Date.now();
    if (this.status === null || now - this.status.at > STATUS_LIFETIME_MS) {
      this.status = { at: now, promise: this.probe() };
    }
    return this.status.promise;
  }

  /** Starts `claude` without a message and reads its initialization: the account and the models. No model request. */
  private async probe(): Promise<ClaudeCodeStatus> {
    const abortController = new AbortController();
    const timer = setTimeout(() => {
      abortController.abort();
    }, STATUS_TIMEOUT_MS);
    const running = this.runQuery({
      prompt: waitForAbort(abortController.signal),
      options: { ...this.baseOptions(), persistSession: false, abortController },
    });
    try {
      const initialization = await running.initializationResult();
      return { account: initialization.account, models: initialization.models, error: null };
    } catch (error) {
      return { account: null, models: [], error: `Claude Code did not start: ${readErrorText(error)}` };
    } finally {
      clearTimeout(timer);
      abortController.abort();
      running.close();
    }
  }

  async providerSummary(): Promise<ProviderSummary> {
    const status = await this.readStatus();
    const models = isLoggedIn(status.account) ? status.models : [];
    return {
      id: CLAUDE_CODE_PROVIDER,
      name: 'Claude Code',
      // The login is not on the web page: Anthropic does not permit a Claude login in another app.
      login_methods: [],
      models: models.map((model) => ({
        id: model.value,
        name: model.displayName,
        thinking_levels: listClaudeThinkingLevels(model),
        reads_images: true,
      })),
    };
  }

  /** The Claude login as a credential for the Credentials dialog. "failed" gives the reason and the login command. */
  async credentialSummary(): Promise<CredentialSummary> {
    const status = await this.readStatus();
    const loggedIn = isLoggedIn(status.account);
    let stateMessage: string | null = null;
    if (status.error !== null) {
      stateMessage = status.error;
    } else if (!loggedIn) {
      stateMessage = `Claude Code is not logged in. Run this command on the server: ${CLAUDE_LOGIN_COMMAND}`;
    }
    return {
      id: CLAUDE_CODE_CREDENTIAL_ID,
      name: status.account?.email ?? 'Claude Code login',
      provider: CLAUDE_CODE_PROVIDER,
      type: 'claude_code',
      key_last4: null,
      state: loggedIn ? 'ready' : 'failed',
      state_message: stateMessage,
    };
  }

  /** The effective thinking level of a run: the requested level, lowered to a level of the model. */
  async effectiveThinkingLevel(modelId: string, requested: ThinkingLevel): Promise<ThinkingLevel> {
    const model = (await this.readStatus()).models.find((item) => item.value === modelId);
    return model === undefined ? requested : lowerThinkingLevel(requested, listClaudeThinkingLevels(model));
  }

  /** Runs one user message to its end. An abort ends the run without an error event. */
  async run(request: ClaudeCodeRunRequest, labels: RunLabels, emit: (event: RunEvent) => void): Promise<void> {
    const { abortController } = request;
    const reader = new RunReader(emit, labels);
    const resume = request.resume && (await this.hasSession(request.sessionId, this.workDir));
    const running = this.runQuery({
      prompt: sendOnce(toUserMessage(request.text, request.images)),
      options: {
        ...this.baseOptions(),
        model: request.model,
        systemPrompt: request.systemPrompt,
        mcpServers: { [TOOL_SERVER]: createToolServer(request.tools, emit, abortController.signal) },
        includePartialMessages: true,
        abortController,
        ...(resume ? { resume: request.sessionId } : { sessionId: request.sessionId }),
        ...thinkingOptions(labels.thinkingLevel),
      },
    });
    try {
      for await (const message of running) {
        reader.read(message);
      }
    } catch (error) {
      if (!abortController.signal.aborted) {
        throw error;
      }
    } finally {
      running.close();
    }
  }

  /** One model call without tools and without a session, for the conversation title. */
  complete(model: string): CompleteText {
    return async (systemPrompt, input) => {
      const running = this.runQuery({
        prompt: input,
        options: {
          ...this.baseOptions(),
          tools: [],
          allowedTools: [],
          model,
          systemPrompt,
          persistSession: false,
          maxTurns: 1,
          thinking: { type: 'disabled' },
        },
      });
      try {
        for await (const message of running) {
          if (message.type === 'result') {
            if (message.subtype === 'success' && !message.is_error) {
              return message.result;
            }
            throw new Error(message.subtype === 'success' ? message.result : message.errors.join(' '));
          }
        }
      } finally {
        running.close();
      }
      throw new Error('Claude Code gave no answer.');
    };
  }

  /** Deletes the Claude Code session of a deleted conversation. A session that does not exist is not an error. */
  async deleteSession(sessionId: string): Promise<void> {
    try {
      await this.removeSession(sessionId, this.workDir);
    } catch {
      // The session file does not exist, for example after a run that did not start.
    }
  }
}
