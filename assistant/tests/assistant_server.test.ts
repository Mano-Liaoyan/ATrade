// The HTTP interface of the assistant service for web (docs/architecture/assistant.md 25.14).
// The Compose health check calls GET /health. The model is a local fake OpenAI-compatible server.
import { mkdtempSync, rmSync } from 'node:fs';
import type { AddressInfo } from 'node:net';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { afterEach, beforeEach, describe, expect, test } from 'vite-plus/test';
import { startAssistantServer } from '../src/assistant_server.ts';
import { Conversations } from '../src/conversations.ts';
import { createFakeOpenModel } from './fake_model.ts';
import { startFakeModelServer, type FakeModelServer, type ModelStep } from './fake_model_server.ts';

const SELECTION = { provider: 'fake', model: 'fake-model', credential_id: 'fake-key-1' };

let workDir: string;
let model: FakeModelServer | undefined;
let close: (() => Promise<void>) | undefined;

beforeEach(() => {
  workDir = mkdtempSync(path.join(tmpdir(), 'atrade-assistant-'));
});

afterEach(async () => {
  await close?.();
  await model?.close();
  model = undefined;
  rmSync(workDir, { recursive: true, force: true });
});

async function startOnFreePort(script: ModelStep[] = []): Promise<string> {
  model = await startFakeModelServer(script);
  const openModel = await createFakeOpenModel(model.baseUrl, workDir);
  const conversations = new Conversations({ piDir: workDir, openModel, createTools: () => [] });
  const server = await startAssistantServer({ host: '127.0.0.1', port: 0 }, conversations);
  close = () =>
    new Promise((resolve) => {
      server.closeAllConnections();
      server.close(() => {
        resolve();
      });
    });
  const { port } = server.address() as AddressInfo;
  return `http://127.0.0.1:${String(port)}`;
}

function postJson(url: string, body: unknown): Promise<Response> {
  return fetch(url, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
}

function readLines(text: string): unknown[] {
  return text
    .split('\n')
    .filter((line) => line !== '')
    .map((line) => JSON.parse(line) as unknown);
}

test('GET /health answers 200 with status ok', async () => {
  const baseUrl = await startOnFreePort();

  const response = await fetch(`${baseUrl}/health`);

  expect(response.status).toBe(200);
  expect(await response.json()).toEqual({ status: 'ok' });
});

test('another path answers 404', async () => {
  const baseUrl = await startOnFreePort();

  const response = await fetch(`${baseUrl}/conversations`);

  expect(response.status).toBe(404);
});

test('a conversation ID that is not a number answers 404', async () => {
  const baseUrl = await startOnFreePort();

  const response = await fetch(`${baseUrl}/conversations/..%2Fsecret/messages`);

  expect(response.status).toBe(404);
});

describe('the conversation routes', () => {
  test('POST runs streams the run events as JSON lines', async () => {
    const baseUrl = await startOnFreePort([{ text: 'Hello.' }]);

    const response = await postJson(`${baseUrl}/conversations/3/runs`, { text: 'Hi.', ...SELECTION });

    expect(response.status).toBe(200);
    expect(response.headers.get('content-type')).toBe('application/x-ndjson');
    expect(readLines(await response.text()).at(-1)).toEqual({
      type: 'message_end',
      text: 'Hello.',
      provider: 'fake',
      model: 'fake-model',
      credential_name: 'Fake API key · first',
    });
  });

  test('POST runs refuses a body without a selection with 400', async () => {
    const baseUrl = await startOnFreePort();

    const response = await postJson(`${baseUrl}/conversations/3/runs`, { text: 'Hi.' });

    expect(response.status).toBe(400);
  });

  test('GET messages reads the messages of the JSONL file', async () => {
    const baseUrl = await startOnFreePort([{ text: 'Hello.' }]);
    await (await postJson(`${baseUrl}/conversations/3/runs`, { text: 'Hi.', ...SELECTION })).text();

    const response = await fetch(`${baseUrl}/conversations/3/messages`);

    expect(await response.json()).toEqual({
      messages: [
        { role: 'user', text: 'Hi.', provider: null, model: null, credential_name: null },
        {
          role: 'assistant',
          text: 'Hello.',
          provider: 'fake',
          model: 'fake-model',
          credential_name: 'Fake API key · first',
        },
      ],
    });
  });

  test('POST steer without an active run answers 409', async () => {
    const baseUrl = await startOnFreePort();

    const response = await postJson(`${baseUrl}/conversations/3/steer`, { text: 'Use SMA 50.' });

    expect(response.status).toBe(409);
  });

  test('POST abort answers 204', async () => {
    const baseUrl = await startOnFreePort();

    const response = await postJson(`${baseUrl}/conversations/3/abort`, {});

    expect(response.status).toBe(204);
  });

  test('POST title answers the title', async () => {
    const baseUrl = await startOnFreePort([{ text: 'Hello.' }, { text: 'Greeting' }]);
    await (await postJson(`${baseUrl}/conversations/3/runs`, { text: 'Hi.', ...SELECTION })).text();

    const response = await postJson(`${baseUrl}/conversations/3/title`, SELECTION);

    expect(await response.json()).toEqual({ title: 'Greeting' });
  });

  test('POST title answers 502 with the reason when the generation fails', async () => {
    const baseUrl = await startOnFreePort();

    const response = await postJson(`${baseUrl}/conversations/3/title`, SELECTION);

    expect(response.status).toBe(502);
    expect(await response.json()).toEqual({ detail: 'The conversation has no answer yet.' });
  });

  test('DELETE removes the messages', async () => {
    const baseUrl = await startOnFreePort([{ text: 'Hello.' }]);
    await (await postJson(`${baseUrl}/conversations/3/runs`, { text: 'Hi.', ...SELECTION })).text();

    const response = await fetch(`${baseUrl}/conversations/3`, { method: 'DELETE' });

    expect(response.status).toBe(204);
    expect(await (await fetch(`${baseUrl}/conversations/3/messages`)).json()).toEqual({ messages: [] });
  });
});
