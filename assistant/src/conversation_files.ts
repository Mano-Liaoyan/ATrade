// The JSONL file of each conversation in the pi directory (docs/architecture/assistant.md 25.8.1).
// pi writes all messages, tool arguments, and tool results into it. PostgreSQL does not hold the messages.
// Each run adds a custom entry with the credential name and the thinking level of the run, so each AI assistant
// message can show its model, its thinking level, and its credential name (25.8.2).
// A Claude Code conversation (25.7.5) keeps its model context in the session of Claude Code. Its JSONL file keeps the
// Claude Code session ID (a custom entry) and the message texts (pi messages with text only), for the message list.
// pi writes the file only when it has a user message or an AI assistant message.
import { existsSync } from 'node:fs';
import path from 'node:path';
import { SessionManager } from '@earendil-works/pi-coding-agent';

export const CREDENTIAL_ENTRY_TYPE = 'atrade_credential';
export const CLAUDE_SESSION_ENTRY_TYPE = 'atrade_claude_session';

/** The runner of a conversation. The first run sets it. A conversation cannot change it (25.7.5). */
export type ConversationRunner = 'pi' | 'claude-code';

export interface ConversationMessage {
  role: 'user' | 'assistant';
  text: string;
  provider: string | null;
  model: string | null;
  credential_name: string | null;
  /** Null for a user message, and for a message of a run before the thinking level was recorded. */
  thinking_level: string | null;
}

/** The data of the custom entry of each run. */
export interface RunEntry {
  credential_name: string;
  thinking_level?: string;
}

/** The data of the Claude Code session entry: the session ID that the next runs resume. */
export interface ClaudeSessionEntry {
  session_id: string;
}

interface LooseMessage {
  role: string;
  content: unknown;
  provider?: string;
  model?: string;
}

type StoredMessage = Parameters<SessionManager['appendMessage']>[0];

const NO_USAGE = {
  input: 0,
  output: 0,
  cacheRead: 0,
  cacheWrite: 0,
  totalTokens: 0,
  cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 },
};

/** A pi user message with text only, for the message list of a Claude Code conversation. */
export function toTextUserMessage(text: string): StoredMessage {
  return { role: 'user', content: [{ type: 'text', text }], timestamp: Date.now() };
}

/** A pi AI assistant message with text only, for the message list of a Claude Code conversation. pi never sends it to
 * a model: a Claude Code conversation does not run in pi. */
export function toTextAssistantMessage(text: string, provider: string, model: string): StoredMessage {
  return {
    role: 'assistant',
    content: [{ type: 'text', text }],
    api: 'anthropic-messages',
    provider,
    model,
    usage: NO_USAGE,
    stopReason: 'stop',
    timestamp: Date.now(),
  };
}

export function conversationDir(piDir: string): string {
  return path.join(piDir, 'conversations');
}

export function conversationFile(piDir: string, conversationId: string): string {
  return path.join(conversationDir(piDir), `${conversationId}.jsonl`);
}

export function openConversationSession(piDir: string, conversationId: string): SessionManager {
  return SessionManager.open(conversationFile(piDir, conversationId), conversationDir(piDir), piDir);
}

/** The text parts of a pi message content, joined. Tool calls and thinking are not text. */
export function readMessageText(content: unknown): string {
  if (typeof content === 'string') {
    return content;
  }
  if (!Array.isArray(content)) {
    return '';
  }
  return (content as { type?: string; text?: string }[])
    .filter((part) => part.type === 'text')
    .map((part) => part.text ?? '')
    .join('');
}

function toConversationMessage(message: LooseMessage, run: RunEntry | null): ConversationMessage | null {
  const text = readMessageText(message.content);
  if (text === '') {
    return null;
  }
  if (message.role === 'user') {
    return { role: 'user', text, provider: null, model: null, credential_name: null, thinking_level: null };
  }
  if (message.role === 'assistant') {
    return {
      role: 'assistant',
      text,
      provider: message.provider ?? null,
      model: message.model ?? null,
      credential_name: run?.credential_name ?? null,
      thinking_level: run?.thinking_level ?? null,
    };
  }
  return null;
}

interface ConversationRecord {
  messages: ConversationMessage[];
  runner: ConversationRunner | null;
  claudeSessionId: string | null;
}

/** Adds a custom entry to the record. Returns the run entry of a pi run, else null. */
function readCustomEntry(record: ConversationRecord, customType: string, content: unknown): RunEntry | null {
  switch (customType) {
    case CREDENTIAL_ENTRY_TYPE:
      return content as RunEntry;
    case CLAUDE_SESSION_ENTRY_TYPE:
      record.runner = 'claude-code';
      record.claudeSessionId = (content as ClaudeSessionEntry).session_id;
      return null;
    default:
      return null;
  }
}

function readConversationRecord(piDir: string, conversationId: string): ConversationRecord {
  const record: ConversationRecord = { messages: [], runner: null, claudeSessionId: null };
  if (!existsSync(conversationFile(piDir, conversationId))) {
    return record;
  }
  let run: RunEntry | null = null;
  for (const entry of openConversationSession(piDir, conversationId).getBranch()) {
    if (entry.type === 'custom') {
      run = readCustomEntry(record, entry.customType, entry.data) ?? run;
    } else if (entry.type === 'message') {
      record.runner ??= 'pi';
      const message = toConversationMessage(entry.message as LooseMessage, run);
      if (message !== null) {
        record.messages.push(message);
      }
    }
  }
  return record;
}

/** The user messages and the AI assistant messages with text, in order. [] when the conversation has no file. */
export function readConversationMessages(piDir: string, conversationId: string): ConversationMessage[] {
  return readConversationRecord(piDir, conversationId).messages;
}

/** The runner of the conversation and its Claude Code session ID. Null runner: the conversation has no run yet. */
export function readConversationRunner(
  piDir: string,
  conversationId: string,
): { runner: ConversationRunner | null; claudeSessionId: string | null } {
  const { runner, claudeSessionId } = readConversationRecord(piDir, conversationId);
  return { runner, claudeSessionId };
}
