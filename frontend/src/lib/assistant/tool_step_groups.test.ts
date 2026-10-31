import { describe, expect, it } from 'vite-plus/test';
import type { LogItem, MessageItem, ToolStepItem } from './conversation_log';
import { describeToolStepGroup, groupToolSteps, type LogEntry } from './tool_step_groups';

const AT = '2026-01-02T03:04:05Z';

function step(id: number, status: ToolStepItem['status'] = 'succeeded', toolName = 'save_strategy_version'): ToolStepItem {
  return { kind: 'tool_step', id, sentAtUtc: AT, toolCallId: `call-${String(id)}`, toolName, status, backtestId: null, backtestStatus: null };
}

function message(id: number): MessageItem {
  return { kind: 'message', id, sentAtUtc: AT, role: 'assistant', text: 'Done.', modelLine: null, streaming: false };
}

function entry(item: LogItem): LogEntry<{ item: LogItem }> {
  return { kind: 'message', message: { item }, continued: false };
}

describe('groupToolSteps', () => {
  it('keeps a single tool step as its own line', () => {
    const entries = [entry(message(0)), entry(step(1)), entry(message(2))];
    expect(groupToolSteps(entries)).toEqual(entries);
  });

  it('puts consecutive tool steps into one group with the ID of the first step', () => {
    const grouped = groupToolSteps([entry(message(0)), entry(step(1)), entry(step(2)), entry(step(3))]);
    expect(grouped).toEqual([entry(message(0)), { kind: 'tool_steps', id: 1, steps: [step(1), step(2), step(3)] }]);
  });

  it('starts a new group after a message or a date divider', () => {
    const divider = { kind: 'divider' as const, dateUtc: '2026-01-03' };
    const grouped = groupToolSteps([entry(step(1)), entry(step(2)), entry(message(3)), entry(step(4)), divider, entry(step(5)), entry(step(6))]);
    expect(grouped).toEqual([
      { kind: 'tool_steps', id: 1, steps: [step(1), step(2)] },
      entry(message(3)),
      entry(step(4)),
      divider,
      { kind: 'tool_steps', id: 5, steps: [step(5), step(6)] },
    ]);
  });
});

describe('describeToolStepGroup', () => {
  it('names the count, with success when all steps succeeded', () => {
    expect(describeToolStepGroup([step(1), step(2)])).toEqual({
      title: '2 tool steps',
      status: 'Succeeded',
      kind: 'success',
      isRunning: false,
    });
  });

  it('runs while one step runs', () => {
    expect(describeToolStepGroup([step(1), step(2, 'running')])).toEqual({
      title: '2 tool steps',
      status: 'Running',
      kind: 'in-progress',
      isRunning: true,
    });
  });

  it('shows the error when a step failed', () => {
    expect(describeToolStepGroup([step(1, 'failed'), step(2)])).toEqual({
      title: '2 tool steps',
      status: 'Failed',
      kind: 'error',
      isRunning: false,
    });
  });
});
