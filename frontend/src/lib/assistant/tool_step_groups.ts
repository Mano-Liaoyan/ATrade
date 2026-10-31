// The tool step groups of the conversation log (docs/architecture/assistant.md 25.12.1): consecutive tool steps
// become one group with a line "<n> tool steps". The group is open while a step runs and closes when all steps end.
// A single tool step stays its own line.
import { describeToolStep, type LogItem, type ToolStepItem, type ToolStepKind } from './conversation_log';

/** An entry of arrangeChatLog (foundation/carbon chat_log.ts). */
export type LogEntry<Message> =
  | { kind: 'divider'; dateUtc: string }
  | { kind: 'message'; message: Message; continued: boolean };

export interface ToolStepGroup {
  kind: 'tool_steps';
  /** The item ID of the first step. */
  id: number;
  steps: ToolStepItem[];
}

export type GroupedLogEntry<Message> = LogEntry<Message> | ToolStepGroup;

function toolStepOf<Message extends { item: LogItem }>(entry: LogEntry<Message>): ToolStepItem | null {
  return entry.kind === 'message' && entry.message.item.kind === 'tool_step' ? entry.message.item : null;
}

/** Puts 2 or more consecutive tool steps into one group. A message or a date divider ends a group. */
export function groupToolSteps<Message extends { item: LogItem }>(
  entries: readonly LogEntry<Message>[],
): GroupedLogEntry<Message>[] {
  const grouped: GroupedLogEntry<Message>[] = [];
  let run: LogEntry<Message>[] = [];
  function endRun(): void {
    const steps = run.map(toolStepOf).filter((step) => step !== null);
    const [first] = steps;
    if (steps.length > 1 && first !== undefined) {
      grouped.push({ kind: 'tool_steps', id: first.id, steps });
    } else {
      grouped.push(...run);
    }
    run = [];
  }
  for (const entry of entries) {
    if (toolStepOf(entry) === null) {
      endRun();
      grouped.push(entry);
    } else {
      run.push(entry);
    }
  }
  endRun();
  return grouped;
}

// The name and tooltip of the status icon of a group.
const GROUP_STATUS_WORDS: Record<ToolStepKind, string> = {
  'in-progress': 'Running',
  error: 'Failed',
  success: 'Succeeded',
  neutral: 'Done',
};

/** The summary line of a group: the count as the title, and one status for all steps as the status icon. */

export function describeToolStepGroup(steps: readonly ToolStepItem[]): {
  title: string;
  status: string;
  kind: ToolStepKind;
  isRunning: boolean;
} {
  const kinds = steps.map((step) => describeToolStep(step).kind);
  const isRunning = steps.some((step) => step.status === 'running') || kinds.includes('in-progress');
  let kind: ToolStepKind = 'neutral';
  if (isRunning) {
    kind = 'in-progress';
  } else if (kinds.includes('error')) {
    kind = 'error';
  } else if (kinds.every((stepKind) => stepKind === 'success')) {
    kind = 'success';
  }
  return { title: `${String(steps.length)} tool steps`, status: GROUP_STATUS_WORDS[kind], kind, isRunning };
}
