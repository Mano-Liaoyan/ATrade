// The web tools of the AI assistant (docs/architecture/assistant.md 25.4.5). No test connects to the internet: each
// call here ends before a request leaves the process.
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import type { ExtensionFactory } from '@earendil-works/pi-coding-agent';
import { afterAll, afterEach, beforeAll, describe, expect, test } from 'vite-plus/test';
import { createAssistantSession } from '../src/assistant_session.ts';
import { loadWebAccess } from '../src/web_access.ts';
import { openFakeModel } from './fake_model.ts';
import { startFakeModelServer, type FakeModelServer, type ModelStep } from './fake_model_server.ts';

// One directory for the file: the extension reads the place of its settings file one time, at its import.
let piDir: string;
let webAccess: ExtensionFactory;
let server: FakeModelServer | undefined;

beforeAll(async () => {
  piDir = mkdtempSync(path.join(tmpdir(), 'atrade-web-access-'));
  webAccess = await loadWebAccess(piDir);
});

afterEach(async () => {
  await server?.close();
  server = undefined;
});

afterAll(() => {
  rmSync(piDir, { recursive: true, force: true });
});

async function runOneMessage(script: ModelStep[], extension: ExtensionFactory | undefined) {
  server = await startFakeModelServer(script);
  const { modelRuntime, model } = await openFakeModel(server.baseUrl, piDir);
  const session = await createAssistantSession({
    modelRuntime,
    model,
    thinkingLevel: 'off',
    piDir,
    customTools: [],
    systemPrompt: 'You are the ATrade strategy assistant.',
    webAccess: extension,
  });
  try {
    await session.prompt('Start.');
  } finally {
    session.dispose();
  }
  return server.requests;
}

function readToolResults(requests: FakeModelServer['requests']): string[] {
  const messages = requests.at(-1)?.messages ?? [];
  return messages.filter((message) => message.role === 'tool').map((message) => JSON.stringify(message.content));
}

function fetchStep(toolArguments: Record<string, unknown>): ModelStep {
  return { toolName: 'fetch_content', toolArguments };
}

describe('the web tools', () => {
  test('the model gets only the 3 web tools', async () => {
    const requests = await runOneMessage([{ text: 'Done.' }], webAccess);

    expect(requests[0]?.tools?.map((tool) => tool.function.name)).toEqual(['web_search', 'fetch_content', 'get_search_content']);
  });

  test('fetch_content refuses the addresses of the host and of the Compose networks', async () => {
    const requests = await runOneMessage(
      [fetchStep({ url: 'http://127.0.0.1:8001/api/strategies' }), fetchStep({ url: 'http://172.31.250.2:8001/api/strategies' }), { text: 'Done.' }],
      webAccess,
    );

    const results = readToolResults(requests);
    expect(results).toHaveLength(2);
    expect(results[0]).toContain('Blocked internal address');
    expect(results[1]).toContain('Blocked internal address');
  });

  test('fetch_content reads no local file', async () => {
    const requests = await runOneMessage(
      [fetchStep({ url: '/etc/hostname' }), fetchStep({ url: 'file:///etc/hostname' }), { text: 'Done.' }],
      webAccess,
    );

    const results = readToolResults(requests);
    expect(results[0]).toContain('Invalid URL');
    expect(results[1]).toContain('Only HTTP and HTTPS URLs');
  });

  test('the tool guard refuses a proxy and a browser cookie profile', async () => {
    const requests = await runOneMessage(
      [
        fetchStep({ url: 'https://example.com', proxy: 'http://127.0.0.1:9' }),
        fetchStep({ url: 'https://example.com', auth: true }),
        { text: 'Done.' },
      ],
      webAccess,
    );

    const results = readToolResults(requests);
    expect(results[0]).toContain('ATrade does not permit the argument proxy.');
    expect(results[1]).toContain('ATrade does not permit the argument auth.');
  });

  test('a session without the extension has no web tool', async () => {
    const requests = await runOneMessage([{ toolName: 'web_search', toolArguments: { query: 'ATrade' } }, { text: 'Done.' }], undefined);

    expect(requests[0]?.tools ?? []).toEqual([]);
    expect(readToolResults(requests)[0]).toMatch(/Tool web_search not found|is not an ATrade assistant tool/);
  });
});
