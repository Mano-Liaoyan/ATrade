// The conversations of the AI assistant (docs/architecture/assistant.md 25.8, 25.10).
// Each run opens the JSONL file of the conversation with the selected model and credential, so the user can change
// the provider, the model, or the credential between 2 messages. One conversation has at most one active run.
// The run events are pi events with only the fields that web needs. web changes them into the /ws/assistant messages.
// A conversation runs in pi or in Claude Code (claude_code.ts, 25.7.5). The first run sets the runner. A conversation
// cannot change it, because the model context of each runner is in its own session.
import { randomUUID } from 'node:crypto';
import { rmSync } from 'node:fs';
import { mkdir } from 'node:fs/promises';
import type { AgentSession, AgentSessionEvent, ExtensionFactory, ToolDefinition } from '@earendil-works/pi-coding-agent';
import { createAssistantSession } from './assistant_session.ts';
import type { UserMessageBudget } from './backtest_tools.ts';
import { CLAUDE_CODE_PROVIDER, type ClaudeCode } from './claude_code.ts';
import {
  CLAUDE_SESSION_ENTRY_TYPE,
  CREDENTIAL_ENTRY_TYPE,
  conversationDir,
  conversationFile,
  openConversationSession,
  readConversationMessages,
  readConversationRunner,
  readMessageText,
  toTextAssistantMessage,
  toTextUserMessage,
  type ClaudeSessionEntry,
  type ConversationMessage,
  type ConversationRunner,
  type RunEntry,
} from './conversation_files.ts';
import { completeWithPi, generateTitle } from './conversation_title.ts';
import type { ModelSelection, OpenModel, ThinkingLevel } from './model_selection.ts';
import { toToolRunEvents, type ToolRunEvent } from './tool_events.ts';

export type RunEvent =
  | { type: 'text_delta'; delta: string }
  | {
      type: 'message_end';
      text: string;
      provider: string;
      model: string;
      credential_name: string;
      thinking_level: string;
    }
  | { type: 'error'; message: string }
  | ToolRunEvent;

/** The tools of one run. The budget counts the backtests of the current user message. */
export type CreateTools = (run: { conversationId: string; budget: UserMessageBudget }) => ToolDefinition[];

/** One image of a user message, in the form of pi. `data` is base64. */
export interface PromptImage {
  type: 'image';
  mimeType: string;
  // eslint-disable-next-line @typescript-eslint/naming-convention -- readability-exception: the field name of pi.
  data: string;
}

export interface RunRequest {
  text: string;
  /** The images of the user message. The JSONL file keeps them, so the next runs also send them to the model. */
  images?: PromptImage[];
  selection: ModelSelection;
  /** The requested thinking level. The model can lower it (assistant_session.ts). */
  thinkingLevel: ThinkingLevel;
  /** The system prompt of the conversation. web makes it from the prompt version and the fixed part. */
  systemPrompt: string;
}

export interface ConversationsOptions {
  /** The directory of the pi files (the volume atrade-assistant-pi in the container). */
  piDir: string;
  openModel: OpenModel;
  createTools: CreateTools;
  /** The web tools of each run (web_access.ts). Default: no web tool. */
  webAccess?: ExtensionFactory;
  /** The Claude Code runner (25.7.5). Default: no Claude Code provider. */
  claudeCode?: ClaudeCode;
}

interface EndedAssistantMessage {
  role: 'assistant';
  content: unknown;
  provider: string;
  model: string;
  stopReason: string;
  errorMessage?: string;
}

function readErrorText(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

/** The credential name and the thinking level of the run, for each message_end event. */
interface RunLabels {
  credentialName: string;
  thinkingLevel: string;
}

/** The run event of one pi message event, or null when web does not need the pi event. */
function toMessageRunEvent(event: AgentSessionEvent, labels: RunLabels): RunEvent | null {
  if (event.type === 'message_update' && event.assistantMessageEvent.type === 'text_delta') {
    return { type: 'text_delta', delta: event.assistantMessageEvent.delta };
  }
  if (event.type !== 'message_end' || event.message.role !== 'assistant') {
    return null;
  }
  const message = event.message as EndedAssistantMessage;
  if (message.stopReason === 'error') {
    return { type: 'error', message: message.errorMessage ?? 'The model provider sent an error.' };
  }
  const text = readMessageText(message.content);
  if (text === '') {
    return null;
  }
  return {
    type: 'message_end',
    text,
    provider: message.provider,
    model: message.model,
    credential_name: labels.credentialName,
    thinking_level: labels.thinkingLevel,
  };
}

/** The run events of one pi event. Empty when web does not need the pi event. */
function toRunEvents(event: AgentSessionEvent, labels: RunLabels): RunEvent[] {
  const messageEvent = toMessageRunEvent(event, labels);
  return messageEvent === null ? toToolRunEvents(event) : [messageEvent];
}

export class Conversations {
  private readonly options: ConversationsOptions;
  /** The active runs. A run is active before its session exists. */
  private readonly activeRuns = new Map<string, Promise<void>>();
  /** The active runs that got an abort before their session existed. */
  private readonly abortedRuns = new Set<string>();
  /** The pi session or the Claude Code run of each active run, for the abort. */
  private readonly sessions = new Map<string, Pick<AgentSession, 'abort'>>();

  constructor(options: ConversationsOptions) {
    this.options = options;
  }

  isRunning(conversationId: string): boolean {
    return this.activeRuns.has(conversationId);
  }

  /** Runs one user message to its end. Each error becomes an error event. */
  async run(conversationId: string, request: RunRequest, emit: (event: RunEvent) => void): Promise<void> {
    if (this.activeRuns.has(conversationId)) {
      emit({ type: 'error', message: 'The conversation has an active run.' });
      return;
    }
    const run = this.runSession(conversationId, request, emit)
      .catch((error: unknown) => {
        emit({ type: 'error', message: readErrorText(error) });
      })
      .finally(() => {
        this.sessions.delete(conversationId);
        this.abortedRuns.delete(conversationId);
        this.activeRuns.delete(conversationId);
      });
    this.activeRuns.set(conversationId, run);
    await run;
  }

  private async runSession(conversationId: string, request: RunRequest, emit: (event: RunEvent) => void) {
    const claudeSessionId = this.checkRunner(conversationId, request.selection);
    if (request.selection.provider === CLAUDE_CODE_PROVIDER) {
      await this.runClaudeCode(conversationId, request, claudeSessionId, emit);
      return;
    }
    const opened = await this.options.openModel(request.selection);
    const images = request.images ?? [];
    if (images.length > 0 && !opened.model.input.includes('image')) {
      throw new Error(`The model ${opened.model.name} does not read images.`);
    }
    await mkdir(conversationDir(this.options.piDir), { recursive: true });
    if (this.abortedRuns.has(conversationId)) {
      return;
    }
    const conversationSession = openConversationSession(this.options.piDir, conversationId);
    const budget: UserMessageBudget = { startedBacktests: 0 };
    const session = await createAssistantSession({
      modelRuntime: opened.modelRuntime,
      model: opened.model,
      thinkingLevel: request.thinkingLevel,
      piDir: this.options.piDir,
      customTools: this.options.createTools({ conversationId, budget }),
      systemPrompt: request.systemPrompt,
      webAccess: this.options.webAccess,
      conversationSession,
    });
    if (this.abortedRuns.has(conversationId)) {
      session.dispose();
      return;
    }
    // The effective thinking level: pi lowers the requested level to a level of the model.
    const labels: RunLabels = { credentialName: opened.credentialName, thinkingLevel: session.thinkingLevel };
    const entry: RunEntry = { credential_name: labels.credentialName, thinking_level: labels.thinkingLevel };
    conversationSession.appendCustomEntry(CREDENTIAL_ENTRY_TYPE, entry);
    this.sessions.set(conversationId, session);
    const unsubscribe = session.subscribe((event) => {
      toRunEvents(event, labels).forEach(emit);
    });
    try {
      await session.prompt(request.text, { images });
    } finally {
      unsubscribe();
      session.dispose();
    }
  }

  /** Refuses a run in the other runner of the conversation. Returns the Claude Code session ID of the conversation. */
  private checkRunner(conversationId: string, selection: ModelSelection): string | null {
    const runner: ConversationRunner = selection.provider === CLAUDE_CODE_PROVIDER ? 'claude-code' : 'pi';
    const stored = readConversationRunner(this.options.piDir, conversationId);
    if (stored.runner !== null && stored.runner !== runner) {
      throw new Error(
        stored.runner === 'claude-code'
          ? 'This conversation runs in Claude Code. Select a Claude Code model, or start a new conversation.'
          : 'This conversation does not run in Claude Code. Start a new conversation for Claude Code.',
      );
    }
    return stored.claudeSessionId;
  }

  private async runClaudeCode(
    conversationId: string,
    request: RunRequest,
    storedSessionId: string | null,
    emit: (event: RunEvent) => void,
  ): Promise<void> {
    const claudeCode = this.options.claudeCode;
    if (claudeCode === undefined) {
      throw new Error('The assistant service has no Claude Code provider.');
    }
    const credential = await claudeCode.credentialSummary();
    if (credential.state !== 'ready') {
      throw new Error(credential.state_message ?? 'Claude Code is not ready.');
    }
    const thinkingLevel = await claudeCode.effectiveThinkingLevel(request.selection.model, request.thinkingLevel);
    await mkdir(conversationDir(this.options.piDir), { recursive: true });
    if (this.abortedRuns.has(conversationId)) {
      return;
    }
    const conversationSession = openConversationSession(this.options.piDir, conversationId);
    const sessionId = storedSessionId ?? randomUUID();
    if (storedSessionId === null) {
      const entry: ClaudeSessionEntry = { session_id: sessionId };
      conversationSession.appendCustomEntry(CLAUDE_SESSION_ENTRY_TYPE, entry);
    }
    const runEntry: RunEntry = { credential_name: credential.name, thinking_level: thinkingLevel };
    conversationSession.appendCustomEntry(CREDENTIAL_ENTRY_TYPE, runEntry);
    conversationSession.appendMessage(toTextUserMessage(request.text));
    const abortController = new AbortController();
    this.sessions.set(conversationId, {
      abort: () => {
        abortController.abort();
        return Promise.resolve();
      },
    });
    const budget: UserMessageBudget = { startedBacktests: 0 };
    await claudeCode.run(
      {
        text: request.text,
        images: request.images ?? [],
        model: request.selection.model,
        thinkingLevel,
        systemPrompt: request.systemPrompt,
        tools: this.options.createTools({ conversationId, budget }),
        sessionId,
        resume: storedSessionId !== null,
        abortController,
      },
      { credentialName: credential.name, thinkingLevel, model: request.selection.model },
      (event) => {
        if (event.type === 'message_end') {
          conversationSession.appendMessage(toTextAssistantMessage(event.text, event.provider, event.model));
        }
        emit(event);
      },
    );
  }

  async abort(conversationId: string): Promise<void> {
    if (!this.activeRuns.has(conversationId)) {
      return;
    }
    const session = this.sessions.get(conversationId);
    if (session === undefined) {
      this.abortedRuns.add(conversationId);
      return;
    }
    await session.abort();
  }

  readMessages(conversationId: string): ConversationMessage[] {
    return readConversationMessages(this.options.piDir, conversationId);
  }

  async generateTitle(conversationId: string, selection: ModelSelection): Promise<string> {
    const messages = this.readMessages(conversationId);
    if (selection.provider === CLAUDE_CODE_PROVIDER) {
      if (this.options.claudeCode === undefined) {
        throw new Error('The assistant service has no Claude Code provider.');
      }
      return generateTitle(messages, this.options.claudeCode.complete(selection.model));
    }
    return generateTitle(messages, completeWithPi(await this.options.openModel(selection)));
  }

  /** Stops the active run and deletes the JSONL file. */
  async delete(conversationId: string): Promise<void> {
    await this.abort(conversationId);
    // The run can still write the file until it ends.
    await this.activeRuns.get(conversationId);
    const { claudeSessionId } = readConversationRunner(this.options.piDir, conversationId);
    if (claudeSessionId !== null) {
      await this.options.claudeCode?.deleteSession(claudeSessionId);
    }
    rmSync(conversationFile(this.options.piDir, conversationId), { force: true });
  }
}
