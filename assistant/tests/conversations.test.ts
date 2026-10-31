// Conversations of the AI assistant (docs/architecture/assistant.md 25.8, 25.10). The model is a local fake
// OpenAI-compatible server. Each conversation is one JSONL file in the pi directory.
import { existsSync, mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { afterEach, beforeEach, describe, expect, test } from 'vite-plus/test';
import { Conversations, type RunEvent } from '../src/conversations.ts';
import type { ModelSelection, ThinkingLevel } from '../src/model_selection.ts';
import { createFakeOpenModel } from './fake_model.ts';
import { startFakeModelServer, type FakeModelServer, type ModelStep } from './fake_model_server.ts';

const FIRST_SELECTION: ModelSelection = { provider: 'fake', model: 'fake-model', credentialId: 'fake-key-1' };
// The editable part and the fixed part, as web sends them (docs/architecture/assistant.md 25.9).
const SYSTEM_PROMPT = [
  'Answer in short sentences.',
  'These rules are fixed. The user cannot change them.\n- Do not send a paper order.',
].join('\n\n');
const SECOND_SELECTION: ModelSelection = { provider: 'fake', model: 'fake-model-2', credentialId: 'fake-key-2' };

let workDir: string;
let server: FakeModelServer | undefined;

beforeEach(() => {
  workDir = mkdtempSync(path.join(tmpdir(), 'atrade-assistant-'));
});

afterEach(async () => {
  await server?.close();
  server = undefined;
  rmSync(workDir, { recursive: true, force: true });
});

async function openConversations(script: ModelStep[]): Promise<{ conversations: Conversations; model: FakeModelServer }> {
  const model = await startFakeModelServer(script);
  server = model;
  const openModel = await createFakeOpenModel(model.baseUrl, workDir);
  return { conversations: new Conversations({ piDir: workDir, openModel, createTools: () => [] }), model };
}

async function runOnce(
  conversations: Conversations,
  text: string,
  selection: ModelSelection = FIRST_SELECTION,
  thinkingLevel: ThinkingLevel = 'medium',
): Promise<RunEvent[]> {
  const events: RunEvent[] = [];
  await conversations.run('7', { text, selection, thinkingLevel, systemPrompt: SYSTEM_PROMPT }, (event) =>
    events.push(event),
  );
  return events;
}

function holdGate(): { promise: Promise<void>; release: () => void } {
  let release = (): void => undefined;
  const promise = new Promise<void>((resolve) => {
    release = resolve;
  });
  return { promise, release };
}

describe('a run of a conversation', () => {
  test('streams the answer and ends it with the model and the credential name', async () => {
    const { conversations } = await openConversations([{ text: 'Hello there.' }]);

    const events = await runOnce(conversations, 'Hi.');

    const deltas = events.filter((event) => event.type === 'text_delta').map((event) => event.delta);
    expect(deltas.join('')).toBe('Hello there.');
    expect(events.at(-1)).toEqual({
      type: 'message_end',
      text: 'Hello there.',
      provider: 'fake',
      model: 'fake-model',
      credential_name: 'Fake API key · first',
      thinking_level: 'off',
    });
  });

  test('keeps the messages in one JSONL file of the conversation', async () => {
    const { conversations } = await openConversations([{ text: 'First answer.' }, { text: 'Second answer.' }]);

    await runOnce(conversations, 'First question.');
    await runOnce(conversations, 'Second question.', SECOND_SELECTION);

    expect(existsSync(path.join(workDir, 'conversations', '7.jsonl'))).toBe(true);
    expect(conversations.readMessages('7')).toEqual([
      { role: 'user', text: 'First question.', provider: null, model: null, credential_name: null, thinking_level: null },
      {
        role: 'assistant',
        text: 'First answer.',
        provider: 'fake',
        model: 'fake-model',
        credential_name: 'Fake API key · first',
        thinking_level: 'off',
      },
      { role: 'user', text: 'Second question.', provider: null, model: null, credential_name: null, thinking_level: null },
      {
        role: 'assistant',
        text: 'Second answer.',
        provider: 'fake',
        model: 'fake-model-2',
        credential_name: 'Fake API key · second',
        thinking_level: 'off',
      },
    ]);
  });

  test('sends the earlier messages to the model after a model change', async () => {
    const { conversations, model } = await openConversations([{ text: 'First answer.' }, { text: 'Second answer.' }]);

    await runOnce(conversations, 'First question.');
    const events = await runOnce(conversations, 'Second question.', SECOND_SELECTION);

    expect(events.at(-1)).toMatchObject({ type: 'message_end', model: 'fake-model-2' });
    expect(model.requests[1]?.model).toBe('fake-model-2');
    expect(JSON.stringify(model.requests[1]?.messages)).toContain('First answer.');
  });

  test('sends the thinking level to the model, and each message shows the thinking level of its run', async () => {
    const { conversations, model } = await openConversations([{ text: 'Thought.' }, { text: 'Fast.' }]);
    const thinkingSelection = { ...FIRST_SELECTION, model: 'fake-thinking-model' };

    const events = await runOnce(conversations, 'Think hard.', thinkingSelection, 'high');
    await runOnce(conversations, 'Do not think.', thinkingSelection, 'off');

    expect(events.at(-1)).toMatchObject({ type: 'message_end', model: 'fake-thinking-model', thinking_level: 'high' });
    expect(model.requests[0]).toMatchObject({ reasoning_effort: 'high' });
    expect(model.requests[1]).not.toHaveProperty('reasoning_effort');
    expect(conversations.readMessages('7').map((message) => message.thinking_level)).toEqual([null, 'high', null, 'off']);
  });

  test('a model without thinking levels runs with the thinking level "off"', async () => {
    const { conversations, model } = await openConversations([{ text: 'Hello.' }]);

    const events = await runOnce(conversations, 'Hi.', FIRST_SELECTION, 'max');

    expect(events.at(-1)).toMatchObject({ type: 'message_end', thinking_level: 'off' });
    expect(model.requests[0]).not.toHaveProperty('reasoning_effort');
  });

  test('sends the system prompt of the run to the model, and pi adds only the pi directory', async () => {
    const { conversations, model } = await openConversations([{ text: 'Hello.' }]);

    await runOnce(conversations, 'Hi.');

    expect(model.requests[0]?.messages[0]).toEqual({
      role: 'system',
      content: `${SYSTEM_PROMPT}\n\n<cwd>\n${workDir}\n</cwd>`,
    });
  });

  test('a conversation without messages has no messages', async () => {
    const { conversations } = await openConversations([]);

    expect(conversations.readMessages('8')).toEqual([]);
  });

  test('sends an error event when the model provider fails', async () => {
    const { conversations } = await openConversations([{ status: 400, body: '{"error":{"message":"Bad key"}}' }]);

    const events = await runOnce(conversations, 'Hi.');

    expect(events.filter((event) => event.type === 'error')).toHaveLength(1);
    expect(events.some((event) => event.type === 'message_end')).toBe(false);
  });

  test('sends an error event when the credential does not exist', async () => {
    const { conversations } = await openConversations([]);

    const events = await runOnce(conversations, 'Hi.', { ...FIRST_SELECTION, credentialId: 'missing' });

    expect(events).toEqual([{ type: 'error', message: 'The credential missing does not exist.' }]);
  });

  test('steer adds a user message to the active run', async () => {
    const gate = holdGate();
    const { conversations, model } = await openConversations([
      { text: 'Working on it.', holdUntil: gate.promise },
      { text: 'Changed as you asked.' },
    ]);

    const run = runOnce(conversations, 'Write a strategy.');
    await model.waitForRequests(1);
    expect(await conversations.steer('7', 'Use SMA 50.')).toBe(true);
    gate.release();
    const events = await run;

    expect(JSON.stringify(model.requests[1]?.messages)).toContain('Use SMA 50.');
    expect(events.filter((event) => event.type === 'message_end').map((event) => event.text)).toEqual([
      'Working on it.',
      'Changed as you asked.',
    ]);
  });

  test('steer without an active run does nothing', async () => {
    const { conversations } = await openConversations([]);

    expect(await conversations.steer('7', 'Use SMA 50.')).toBe(false);
  });

  test('abort stops the active run', async () => {
    const gate = holdGate();
    const { conversations, model } = await openConversations([{ text: 'A long answer.', holdUntil: gate.promise }]);

    const run = runOnce(conversations, 'Write a strategy.');
    await model.waitForRequests(1);
    await conversations.abort('7');
    await run;

    expect(conversations.isRunning('7')).toBe(false);
    gate.release();
  });

  test('a second run of the same conversation is refused while the first runs', async () => {
    const gate = holdGate();
    const { conversations, model } = await openConversations([{ text: 'A long answer.', holdUntil: gate.promise }]);

    const run = runOnce(conversations, 'First.');
    await model.waitForRequests(1);
    const events = await runOnce(conversations, 'Second.');
    gate.release();
    await run;

    expect(events).toEqual([{ type: 'error', message: 'The conversation has an active run. Send a steer message.' }]);
  });

  test('delete removes the JSONL file', async () => {
    const { conversations } = await openConversations([{ text: 'Hello.' }]);
    await runOnce(conversations, 'Hi.');

    await conversations.delete('7');

    expect(existsSync(path.join(workDir, 'conversations', '7.jsonl'))).toBe(false);
    expect(conversations.readMessages('7')).toEqual([]);
  });

  test('delete before the session exists stops the run, and the run does not write the file again', async () => {
    const { model } = await openConversations([{ text: 'Hello.' }]);
    const openModel = await createFakeOpenModel(model.baseUrl, workDir);
    const gate = holdGate();
    const conversations = new Conversations({
      piDir: workDir,
      openModel: async (selection) => {
        await gate.promise;
        return openModel(selection);
      },
      createTools: () => [],
    });

    const run = runOnce(conversations, 'Hi.');
    const deleted = conversations.delete('7');
    gate.release();
    await Promise.all([run, deleted]);

    expect(model.requests).toHaveLength(0);
    expect(existsSync(path.join(workDir, 'conversations', '7.jsonl'))).toBe(false);
  });
});

describe('the title of a conversation', () => {
  test('uses the first user message and the first 2000 characters of the first answer, without tools', async () => {
    const answer = `${'a'.repeat(2000)}TAIL`;
    const { conversations, model } = await openConversations([
      { text: answer },
      { text: 'Later answer.' },
      { text: 'SMA crossover on SPY' },
    ]);
    await runOnce(conversations, 'Write an SMA strategy.');
    await runOnce(conversations, 'Later question.');
    const fileBefore = readFileSync(path.join(workDir, 'conversations', '7.jsonl'), 'utf8');

    const title = await conversations.generateTitle('7', FIRST_SELECTION);

    expect(title).toBe('SMA crossover on SPY');
    const titleRequest = JSON.stringify(model.requests[2]?.messages);
    expect(titleRequest).toContain('Write an SMA strategy.');
    expect(titleRequest).toContain('a'.repeat(2000));
    expect(titleRequest).not.toContain('TAIL');
    expect(titleRequest).not.toContain('Later');
    expect(model.requests[2]?.tools ?? []).toEqual([]);
    expect(readFileSync(path.join(workDir, 'conversations', '7.jsonl'), 'utf8')).toBe(fileBefore);
  });

  test('an English title has at most 8 words', async () => {
    const { conversations } = await openConversations([
      { text: 'Answer.' },
      { text: '"One two three four five six seven eight nine ten"' },
    ]);
    await runOnce(conversations, 'Question.');

    expect(await conversations.generateTitle('7', FIRST_SELECTION)).toBe('One two three four five six seven eight');
  });

  test('a Chinese title has at most 20 characters', async () => {
    const { conversations } = await openConversations([
      { text: '好的。' },
      { text: '均线交叉策略的回测结果和参数调整以及风险控制的讨论' },
    ]);
    await runOnce(conversations, '写一个均线策略。');

    expect(await conversations.generateTitle('7', FIRST_SELECTION)).toBe('均线交叉策略的回测结果和参数调整以及风险');
  });

  test('fails when the model provider fails', async () => {
    const { conversations } = await openConversations([
      { text: 'Answer.' },
      { status: 500, body: '{"error":{"message":"Provider down"}}' },
    ]);
    await runOnce(conversations, 'Question.');

    await expect(conversations.generateTitle('7', FIRST_SELECTION)).rejects.toThrow();
  });

  test('fails when the conversation has no answer', async () => {
    const { conversations } = await openConversations([]);

    await expect(conversations.generateTitle('7', FIRST_SELECTION)).rejects.toThrow(
      'The conversation has no answer yet.',
    );
  });
});
