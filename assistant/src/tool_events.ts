// The run events of the tool calls (docs/architecture/assistant.md 25.10, 25.14). web changes them into the
// /ws/assistant messages tool_step, strategy_version_saved, backtest_finished, screen_saved, and screen_run_finished.
import type { AgentSessionEvent } from '@earendil-works/pi-coding-agent';
import type { SavedScreen, ScreenRun, ToolDetails } from './tool_results.ts';

export interface ToolStepEvent {
  type: 'tool_step';
  tool_call_id: string;
  tool_name: string;
  /** running at the start and at each onUpdate. succeeded or failed at the end. */
  status: 'running' | 'succeeded' | 'failed';
  /** run_backtest only: the backtest ID and its queue state or run state. Else null. */
  backtest_id: number | null;
  backtest_status: string | null;
}

export type ToolRunEvent =
  | ToolStepEvent
  | { type: 'strategy_version_saved'; strategy_id: number; strategy_version_id: number; version_number: number }
  | { type: 'backtest_finished'; backtest_id: number }
  | ({ type: 'screen_saved' } & SavedScreen)
  | ({ type: 'screen_run_finished' } & ScreenRun);

function readDetails(result: unknown): ToolDetails {
  const details = (result as { details?: unknown } | undefined)?.details;
  return typeof details === 'object' && details !== null ? details : {};
}

function toolStep(
  event: { toolCallId: string; toolName: string },
  status: ToolStepEvent['status'],
  details: ToolDetails,
): ToolStepEvent {
  return {
    type: 'tool_step',
    tool_call_id: event.toolCallId,
    tool_name: event.toolName,
    status,
    backtest_id: details.backtest?.id ?? null,
    backtest_status: details.backtest?.status ?? null,
  };
}

/** The run events of one pi event. Empty for a pi event that is not a tool event. */
export function toToolRunEvents(event: AgentSessionEvent): ToolRunEvent[] {
  switch (event.type) {
    case 'tool_execution_start':
      return [toolStep(event, 'running', {})];
    case 'tool_execution_update':
      return [toolStep(event, 'running', readDetails(event.partialResult))];
    case 'tool_execution_end': {
      const details = readDetails(event.result);
      const events: ToolRunEvent[] = [toolStep(event, event.isError ? 'failed' : 'succeeded', details)];
      if (details.savedVersion !== undefined) {
        events.push({ type: 'strategy_version_saved', ...details.savedVersion });
      }
      if (details.finishedBacktestId !== undefined) {
        events.push({ type: 'backtest_finished', backtest_id: details.finishedBacktestId });
      }
      if (details.savedScreen !== undefined) {
        events.push({ type: 'screen_saved', ...details.savedScreen });
      }
      if (details.screenRun !== undefined) {
        events.push({ type: 'screen_run_finished', ...details.screenRun });
      }
      return events;
    }
    default:
      return [];
  }
}
