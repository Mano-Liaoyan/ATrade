// The conversations of the AI assistant (docs/architecture/assistant.md 25.8, 25.10).
// Each run opens the JSONL file of the conversation with the selected model and credential, so the user can change
// the provider, the model, or the credential between 2 messages. One conversation has at most one active run.
// The run events are pi events with only the fields that web needs. web changes them into the /ws/assistant messages.
import { rmSync } from 'node:fs';
import { mkdir } from 'node:fs/promises';
import type { AgentSession, AgentSessionEvent, ToolDefinition } from '@earendil-works/pi-coding-agent';
import { createAssistantSession } from './assistant_session.ts';
import {
  CREDENTIAL_ENTRY_TYPE,
  conversationDir,
  conversationFile,
  openConversationSession,
  readConversationMessages,
  readMessageText,
  type ConversationMessage,
} from './conversation_files.ts';
import { generateTitle } from './conversation_title.ts';
import type { ModelSelection, OpenModel } from './model_selection.ts';

export type RunEvent =
  | { type: 'text_delta'; delta: string }
  | { type: 'message_end'; text: string; provider: string; model: string; credential_name: string }
  | { type: 'error'; message: string };

export interface RunRequest {
  text: string;
  selection: ModelSelection;
  /** The system prompt of the conversation. web makes it from the prompt version and the fixed part. */
  systemPrompt: string;
}

export interface ConversationsOptions {
  /** The directory of the pi files (the volume atrade-assistant-pi in the container). */
  piDir: string;
  openModel: OpenModel;
  customTools: ToolDefinition[];
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

/** The run event of one pi event, or null when web does not need the pi event. */
function toRunEvent(event: AgentSessionEvent, credentialName: string): RunEvent | null {
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
  return { type: 'message_end', text, provider: message.provider, model: message.model, credential_name: credentialName };
}

export class Conversations {
  private readonly options: ConversationsOptions;
  /** The active runs. A run is active before its session exists. */
  private readonly activeRuns = new Map<string, Promise<void>>();
  /** The active runs that got an abort before their session existed. */
  private readonly abortedRuns = new Set<string>();
  private readonly sessions = new Map<string, AgentSession>();

  constructor(options: ConversationsOptions) {
    this.options = options;
  }

  isRunning(conversationId: string): boolean {
    return this.activeRuns.has(conversationId);
  }

  /** Runs one user message to its end. Each error becomes an error event. */
  async run(conversationId: string, request: RunRequest, emit: (event: RunEvent) => void): Promise<void> {
    if (this.activeRuns.has(conversationId)) {
      emit({ type: 'error', message: 'The conversation has an active run. Send a steer message.' });
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
    const opened = await this.options.openModel(request.selection);
    await mkdir(conversationDir(this.options.piDir), { recursive: true });
    if (this.abortedRuns.has(conversationId)) {
      return;
    }
    const conversationSession = openConversationSession(this.options.piDir, conversationId);
    conversationSession.appendCustomEntry(CREDENTIAL_ENTRY_TYPE, { credential_name: opened.credentialName });
    const session = await createAssistantSession({
      modelRuntime: opened.modelRuntime,
      model: opened.model,
      piDir: this.options.piDir,
      customTools: this.options.customTools,
      systemPrompt: request.systemPrompt,
      conversationSession,
    });
    if (this.abortedRuns.has(conversationId)) {
      session.dispose();
      return;
    }
    this.sessions.set(conversationId, session);
    const unsubscribe = session.subscribe((event) => {
      const runEvent = toRunEvent(event, opened.credentialName);
      if (runEvent !== null) {
        emit(runEvent);
      }
    });
    try {
      await session.prompt(request.text);
    } finally {
      unsubscribe();
      session.dispose();
    }
  }

  /** Adds a user message to the active run. False when the conversation has no active run. */
  async steer(conversationId: string, text: string): Promise<boolean> {
    const session = this.sessions.get(conversationId);
    if (session === undefined) {
      return false;
    }
    await session.steer(text);
    return true;
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
    return generateTitle(messages, await this.options.openModel(selection));
  }

  /** Stops the active run and deletes the JSONL file. */
  async delete(conversationId: string): Promise<void> {
    await this.abort(conversationId);
    // The run can still write the file until it ends.
    await this.activeRuns.get(conversationId);
    rmSync(conversationFile(this.options.piDir, conversationId), { force: true });
  }
}
