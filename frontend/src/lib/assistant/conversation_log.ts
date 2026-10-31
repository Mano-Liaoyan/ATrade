// The items of the conversation log in the assistant side column (docs/architecture/assistant.md 25.12.1): the
// messages, the tool steps, the diff cards, the metric cards, and the condition cards (25.12.4). The /ws/assistant messages change the log
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
  | Schemas['BacktestFinishedMessage']
  | Schemas['ScreenSavedMessage']
  | Schemas['ScreenRunFinishedMessage'];

/** The status icon kinds of a tool step. */
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
  /** "model · thinking level · credential name" under an AI assistant message. Null for a user message. */
  modelLine: string | null;
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

export interface ScreenCounts {
  start_count: number;
  after_filters_count: number;
  after_indicator_conditions_count: number;
  result_count: number;
}

/** A condition card: the screen as the AI assistant saved it, and the definition that the card compares with. */
export interface ScreenItem extends ItemBase {
  kind: 'screen';
  screenId: number;
  name: string;
  market: string;
  definition: Schemas['JsonValue'];
  previousDefinition: Schemas['JsonValue'];
  /** The funnel counts of the last run_screen of the screen after this save. Null before a run. */
  counts: ScreenCounts | null;
}

export type LogItem = MessageItem | ToolStepItem | DiffItem | MetricsItem | ScreenItem;

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
interface MessageModel {
  model: string | null;
  credential_name: string | null;
  thinking_level?: string | null;
}

/** The level "off" (a model without reasoning, or no thinking) adds nothing to the line. */
function formatModelLine(message: MessageModel): string | null {
  if (message.model === null) {
    return null;
  }
  const thinking = message.thinking_level === 'off' ? null : (message.thinking_level ?? null);
  return [message.model, thinking, message.credential_name].filter((part) => part !== null).join(' · ');
}

export function readConversationLog(messages: readonly SavedMessage[], createdAtUtc: string): ConversationLog {
  return messages.reduce<ConversationLog>(
    (log, message) =>
      append(
        log,
        {
          kind: 'message',
          role: message.role,
          text: message.text,
          modelLine: formatModelLine(message),
          streaming: false,
        },
        createdAtUtc,
      ),
    EMPTY_LOG,
  );
}

export function addUserMessage(log: ConversationLog, text: string, sentAtUtc: string): ConversationLog {
  return append(log, { kind: 'message', role: 'user', text, modelLine: null, streaming: false }, sentAtUtc);
}

function findStreamingMessage(log: ConversationLog): MessageItem | null {
  const last = log.items.at(-1);
  return last?.kind === 'message' && last.streaming ? last : null;
}

function addDelta(log: ConversationLog, text: string, sentAtUtc: string): ConversationLog {
  const streaming = findStreamingMessage(log);
  if (streaming === null) {
    return append(log, { kind: 'message', role: 'assistant', text, modelLine: null, streaming: true }, sentAtUtc);
  }
  return replaceLast(log, { ...streaming, text: streaming.text + text });
}

function endMessage(log: ConversationLog, message: Schemas['MessageEndMessage'], sentAtUtc: string): ConversationLog {
  const ended = { text: message.text, modelLine: formatModelLine(message), streaming: false };
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

function addScreenCounts(log: ConversationLog, message: Schemas['ScreenRunFinishedMessage']): ConversationLog {
  const index = log.items.findLastIndex((item) => item.kind === 'screen' && item.screenId === message.screen_id);
  const card = log.items[index];
  if (card?.kind !== 'screen') {
    return log;
  }
  const counts: ScreenCounts = {
    start_count: message.start_count,
    after_filters_count: message.after_filters_count,
    after_indicator_conditions_count: message.after_indicator_conditions_count,
    result_count: message.result_count,
  };
  return { ...log, items: log.items.with(index, { ...card, counts }) };
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
    case 'screen_saved':
      return append(
        endStreaming(log),
        {
          kind: 'screen',
          screenId: message.screen_id,
          name: message.name,
          market: message.market,
          definition: message.definition,
          previousDefinition: message.previous_definition,
          counts: null,
        },
        sentAtUtc,
      );
    case 'screen_run_finished':
      return addScreenCounts(log, message);
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

/**
 * The line of a tool step: the title, for example "Backtest #42", after a status icon. `status` is the name and the
 * tooltip of the icon, for example "Running".
 */
export function describeToolStep(step: ToolStepFields): { title: string; status: string; kind: ToolStepKind } {
  if (step.backtestId !== null && step.backtestStatus !== null) {
    return {
      title: `Backtest #${String(step.backtestId)}`,
      status: toWords(step.backtestStatus),
      kind: findBacktestStateKind(step.backtestStatus, step.status),
    };
  }
  return { title: toWords(step.toolName), status: toWords(step.status), kind: findToolStateKind(step.status) };
}
