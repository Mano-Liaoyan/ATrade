// The items of the conversation log in the assistant side column (docs/architecture/assistant.md 25.12.1): the
// messages, the tool steps, the diff cards, and the metric cards. The /ws/assistant messages change the log
// (25.10). The saved messages of a conversation have only text (25.11), so a reopened conversation shows no tool step
// and no card.
import type { components } from '#lib/api';

type Schemas = components['schemas'];
export type SavedMessage = Schemas['ConversationMessageResponse'];
export type ServerMessage =
  | Schemas['MessageDeltaMessage']
  | Schemas['MessageEndMessage']
  | Schemas['RunStateMessage']
  | Schemas['ToolStepMessage']
  | Schemas['StrategyVersionSavedMessage']
  | Schemas['BacktestFinishedMessage'];

/** The StatusIndicator kinds of a tool step. */
export type ToolStepKind = 'success' | 'in-progress' | 'error' | 'neutral';

interface ItemBase {
  id: number;
  /** ISO 8601 time in UTC, for the date dividers of the log. */
  sentAtUtc: string;
}

export interface MessageItem extends ItemBase {
  kind: 'message';
  role: 'user' | 'assistant';
  text: string;
  model: string | null;
  credentialName: string | null;
  streaming: boolean;
}

export interface ToolStepFields {
  toolName: string;
  status: Schemas['ToolStepMessage']['status'];
  backtestId: number | null;
  backtestStatus: string | null;
}

export interface ToolStepItem extends ItemBase, ToolStepFields {
  kind: 'tool_step';
  toolCallId: string;
}

export interface DiffItem extends ItemBase {
  kind: 'diff';
  strategyId: number;
  versionNumber: number;
}

export interface MetricsItem extends ItemBase {
  kind: 'metrics';
  backtestId: number;
}

export type LogItem = MessageItem | ToolStepItem | DiffItem | MetricsItem;

export interface ConversationLog {
  items: LogItem[];
  isRunning: boolean;
  nextId: number;
}

export const EMPTY_LOG: ConversationLog = { items: [], isRunning: false, nextId: 0 };

type NewItem = LogItem extends infer Item ? (Item extends LogItem ? Omit<Item, 'id' | 'sentAtUtc'> : never) : never;

function append(log: ConversationLog, item: NewItem, sentAtUtc: string): ConversationLog {
  return { ...log, items: [...log.items, { ...item, id: log.nextId, sentAtUtc }], nextId: log.nextId + 1 };
}

function replaceLast(log: ConversationLog, item: LogItem): ConversationLog {
  return { ...log, items: [...log.items.slice(0, -1), item] };
}

/** The saved messages of a conversation. They have no time, so they get the creation time of the conversation. */
export function readConversationLog(messages: readonly SavedMessage[], createdAtUtc: string): ConversationLog {
  return messages.reduce<ConversationLog>(
    (log, message) =>
      append(
        log,
        {
          kind: 'message',
          role: message.role,
          text: message.text,
          model: message.model,
          credentialName: message.credential_name,
          streaming: false,
        },
        createdAtUtc,
      ),
    EMPTY_LOG,
  );
}

export function addUserMessage(log: ConversationLog, text: string, sentAtUtc: string): ConversationLog {
  return append(log, { kind: 'message', role: 'user', text, model: null, credentialName: null, streaming: false }, sentAtUtc);
}

function findStreamingMessage(log: ConversationLog): MessageItem | null {
  const last = log.items.at(-1);
  return last?.kind === 'message' && last.streaming ? last : null;
}

function addDelta(log: ConversationLog, text: string, sentAtUtc: string): ConversationLog {
  const streaming = findStreamingMessage(log);
  if (streaming === null) {
    return append(log, { kind: 'message', role: 'assistant', text, model: null, credentialName: null, streaming: true }, sentAtUtc);
  }
  return replaceLast(log, { ...streaming, text: streaming.text + text });
}

function endMessage(log: ConversationLog, message: Schemas['MessageEndMessage'], sentAtUtc: string): ConversationLog {
  const ended = { text: message.text, model: message.model, credentialName: message.credential_name, streaming: false };
  const streaming = findStreamingMessage(log);
  if (streaming === null) {
    return append(log, { kind: 'message', role: 'assistant', ...ended }, sentAtUtc);
  }
  return replaceLast(log, { ...streaming, ...ended });
}

/** A text part after a tool step starts a new message, so the streaming message ends at each other item. */
function endStreaming(log: ConversationLog): ConversationLog {
  const streaming = findStreamingMessage(log);
  return streaming === null ? log : replaceLast(log, { ...streaming, streaming: false });
}

function addToolStep(log: ConversationLog, message: Schemas['ToolStepMessage'], sentAtUtc: string): ConversationLog {
  const fields = {
    toolName: message.tool_name,
    status: message.status,
    backtestId: message.backtest_id,
    backtestStatus: message.backtest_status,
  };
  if (!log.items.some((item) => item.kind === 'tool_step' && item.toolCallId === message.tool_call_id)) {
    return append(endStreaming(log), { kind: 'tool_step', toolCallId: message.tool_call_id, ...fields }, sentAtUtc);
  }
  return {
    ...log,
    items: log.items.map((item) => (item.kind === 'tool_step' && item.toolCallId === message.tool_call_id ? { ...item, ...fields } : item)),
  };
}

export function addServerMessage(log: ConversationLog, message: ServerMessage, sentAtUtc: string): ConversationLog {
  switch (message.type) {
    case 'message_delta':
      return addDelta(log, message.text, sentAtUtc);
    case 'message_end':
      return endMessage(log, message, sentAtUtc);
    case 'run_state':
      return message.state === 'running' ? { ...log, isRunning: true } : { ...endStreaming(log), isRunning: false };
    case 'tool_step':
      return addToolStep(log, message, sentAtUtc);
    case 'strategy_version_saved':
      return append(
        endStreaming(log),
        { kind: 'diff', strategyId: message.strategy_id, versionNumber: message.version_number },
        sentAtUtc,
      );
    case 'backtest_finished':
      return append(endStreaming(log), { kind: 'metrics', backtestId: message.backtest_id }, sentAtUtc);
  }
}

function findToolStateKind(status: ToolStepFields['status']): ToolStepKind {
  switch (status) {
    case 'running':
      return 'in-progress';
    case 'succeeded':
      return 'success';
    case 'failed':
      return 'error';
  }
}

function findBacktestStateKind(backtestStatus: string, status: ToolStepFields['status']): ToolStepKind {
  switch (backtestStatus) {
    case 'queued':
      return 'neutral';
    case 'running':
      return 'in-progress';
    case 'finished':
      return 'success';
    case 'failed':
    case 'timed_out':
      return 'error';
    default:
      return findToolStateKind(status);
  }
}

function toWords(name: string): string {
  const words = name.replaceAll('_', ' ');
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/** The StatusIndicator of a tool step, for example "Backtest #42 running". */
export function describeToolStep(step: ToolStepFields): { label: string; kind: ToolStepKind } {
  if (step.backtestId !== null && step.backtestStatus !== null) {
    return {
      label: `Backtest #${String(step.backtestId)} ${step.backtestStatus.replaceAll('_', ' ')}`,
      kind: findBacktestStateKind(step.backtestStatus, step.status),
    };
  }
  return { label: `${toWords(step.toolName)} ${step.status}`, kind: findToolStateKind(step.status) };
}
