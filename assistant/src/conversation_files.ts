// The JSONL file of each conversation in the pi directory (docs/architecture/assistant.md 25.8.1).
// pi writes all messages, tool arguments, and tool results into it. PostgreSQL does not hold the messages.
// Each run adds a custom entry with the credential name and the thinking level of the run, so each AI assistant
// message can show its model, its thinking level, and its credential name (25.8.2).
import { existsSync } from 'node:fs';
import path from 'node:path';
import { SessionManager } from '@earendil-works/pi-coding-agent';

export const CREDENTIAL_ENTRY_TYPE = 'atrade_credential';

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

interface LooseMessage {
  role: string;
  content: unknown;
  provider?: string;
  model?: string;
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

/** The user messages and the AI assistant messages with text, in order. [] when the conversation has no file. */
export function readConversationMessages(piDir: string, conversationId: string): ConversationMessage[] {
  if (!existsSync(conversationFile(piDir, conversationId))) {
    return [];
  }
  const messages: ConversationMessage[] = [];
  let run: RunEntry | null = null;
  for (const entry of openConversationSession(piDir, conversationId).getBranch()) {
    if (entry.type === 'custom' && entry.customType === CREDENTIAL_ENTRY_TYPE) {
      run = entry.data as RunEntry;
    } else if (entry.type === 'message') {
      const message = toConversationMessage(entry.message as LooseMessage, run);
      if (message !== null) {
        messages.push(message);
      }
    }
  }
  return messages;
}
