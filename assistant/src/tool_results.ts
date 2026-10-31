// The tool results that the model gets, and the details that become /ws/assistant messages (tool_events.ts).
import type { AgentToolResult } from '@earendil-works/pi-coding-agent';
import type { WebPortAnswer } from './web_port_client.ts';

const HTTP_OK_FIRST = 200;
const HTTP_OK_LAST = 299;

/** The structured part of a tool result. pi keeps it out of the model text. web reads it from the run events. */
export interface ToolDetails {
  /** The backtest of run_backtest, with its queue state or run state (queued, running, or a final status). */
  backtest?: { id: number; status: string };
  /** The strategy version that save_strategy_version saved, for the diff card. */
  savedVersion?: { strategy_id: number; strategy_version_id: number; version_number: number };
  /** The backtest that run_backtest waited for to its end, for the metric card. */
  finishedBacktestId?: number;
  /** The screen that create_screen or update_screen saved, for the condition card (25.12.4). */
  savedScreen?: SavedScreen;
  /** The funnel counts of the screen result of run_screen, for the condition card. */
  screenRun?: ScreenRun;
}

export interface SavedScreen {
  screen_id: number;
  name: string;
  market: string;
  definition: unknown;
  /** The screen before update_screen, or the source screen of create_screen. Null without a source screen. */
  previous_definition: unknown;
}

export interface ScreenRun {
  screen_id: number;
  screen_result_id: number;
  start_count: number;
  after_filters_count: number;
  after_indicator_conditions_count: number;
  result_count: number;
}

export type ToolResult = AgentToolResult<ToolDetails>;

export function isSuccess(answer: WebPortAnswer): boolean {
  return answer.status >= HTTP_OK_FIRST && answer.status <= HTTP_OK_LAST;
}

export function textResult(value: unknown, details: ToolDetails = {}): ToolResult {
  const text = typeof value === 'string' ? value : JSON.stringify(value);
  return { content: [{ type: 'text', text }], details };
}

export function errorResult(text: string, details: ToolDetails = {}): ToolResult {
  return { ...textResult(text, details), isError: true };
}

/** The answer body for a success. For a refusal, an error with the status and the body (for example the 422
 * problem list `{"problems": [{"line", "message"}]}` of a strategy version save). */
export function answerResult(answer: WebPortAnswer, details: ToolDetails = {}): ToolResult {
  if (isSuccess(answer)) {
    return textResult(answer.body, details);
  }
  return errorResult(`Port 8001 answered ${String(answer.status)}: ${JSON.stringify(answer.body)}`, details);
}
