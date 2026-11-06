// The contract of the event lines of the assistant service (docs/architecture/assistant.md 25.14). The real emitters
// must give each line of event_lines.json. backend/tests/assistant/test_event_lines.py reads the same file.
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { afterEach, beforeEach, expect, test } from 'vite-plus/test';
import { Conversations, type RunEvent } from '../src/conversations.ts';
import { CredentialFile } from '../src/credential_file.ts';
import { Logins, type LoginEvent } from '../src/logins.ts';
import type { ModelSelection } from '../src/model_selection.ts';
import { toToolRunEvents } from '../src/tool_events.ts';
import EVENT_LINES from './event_lines.json' with { type: 'json' };
import { createFakeOpenModel } from './fake_model.ts';
import { startFakeModelServer, type FakeModelServer } from './fake_model_server.ts';
import { createFakeRuntimeFactory, FAKE_OAUTH_PROVIDER } from './fake_providers.ts';

// tsc fails here when an event type has no line in the file.
const LINES: Record<RunEvent['type'] | LoginEvent['type'], unknown> = EVENT_LINES;
const SELECTION: ModelSelection = { provider: 'fake', model: 'fake-model', credentialId: 'fake-key-1' };
const REQUEST = { text: 'Hi.', selection: SELECTION, thinkingLevel: 'off', systemPrompt: 'Be short.' } as const;

let workDir: string;
let server: FakeModelServer | undefined;

beforeEach(() => {
  workDir = mkdtempSync(path.join(tmpdir(), 'atrade-event-lines-'));
});

afterEach(async () => {
  await server?.close();
  server = undefined;
  rmSync(workDir, { recursive: true, force: true });
});

/** The tool details without `type`. With `type`, the spread in tool_events.ts hides a renamed event. */
function fieldsOf(line: { type: string }): object {
  const fields: Partial<typeof line> = { ...line };
  delete fields.type;
  return fields;
}

test('a run emits the text and message end lines', async () => {
  server = await startFakeModelServer([{ text: 'Hello.' }]);
  const openModel = await createFakeOpenModel(server.baseUrl, workDir);
  const events: RunEvent[] = [];

  await new Conversations({ piDir: workDir, openModel, createTools: () => [] }).run('7', REQUEST, (event) => events.push(event));

  expect(events).toEqual([LINES.text_delta, LINES.message_end]);
});

test('a failed run emits the error line', async () => {
  const openModel = (): Promise<never> => Promise.reject(new Error(EVENT_LINES.error.message));
  const events: RunEvent[] = [];

  await new Conversations({ piDir: workDir, openModel, createTools: () => [] }).run('7', REQUEST, (event) => events.push(event));

  expect(events).toEqual([LINES.error]);
});

test('the end of a tool call emits the tool lines', () => {
  const details = {
    backtest: { id: EVENT_LINES.tool_step.backtest_id, status: EVENT_LINES.tool_step.backtest_status },
    savedVersion: fieldsOf(EVENT_LINES.strategy_version_saved),
    finishedBacktestId: EVENT_LINES.backtest_finished.backtest_id,
    savedScreen: fieldsOf(EVENT_LINES.screen_saved),
    screenRun: fieldsOf(EVENT_LINES.screen_run_finished),
  };

  const events = toToolRunEvents({
    type: 'tool_execution_end',
    toolCallId: EVENT_LINES.tool_step.tool_call_id,
    toolName: EVENT_LINES.tool_step.tool_name,
    result: { details },
    isError: false,
  });

  expect(events).toEqual([
    LINES.tool_step,
    LINES.strategy_version_saved,
    LINES.backtest_finished,
    LINES.screen_saved,
    LINES.screen_run_finished,
  ]);
});

test('a login emits the login lines', async () => {
  const file = new CredentialFile(path.join(workDir, 'credentials.json'));
  const logins = new Logins({ file, createRuntime: createFakeRuntimeFactory(), deviceIdFile: path.join(workDir, 'device-id') });
  const events: LoginEvent[] = [];

  await logins.login({ provider: FAKE_OAUTH_PROVIDER, method: 'oauth', name: 'Personal' }, (event) => {
    events.push(event);
    if (event.type === 'login_step' && event.prompt_id !== null) {
      logins.answer(event.prompt_id, 'CODE42');
    }
  });

  expect(events[0]).toEqual(LINES.login_step);
  const { login_end: line } = EVENT_LINES;
  const anyId: unknown = expect.any(String);
  expect(events.at(-1)).toEqual({ ...line, credential: { ...line.credential, id: anyId } });
});
