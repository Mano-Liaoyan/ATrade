// pi has no built-in tools, refuses each tool that is not in the tool list, and reads no project files
// (docs/architecture/assistant.md 25.2.1). The model is a local fake OpenAI-compatible server.
import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { defineTool } from '@earendil-works/pi-coding-agent';
import { Type } from 'typebox';
import { afterEach, beforeEach, describe, expect, test } from 'vite-plus/test';
import { createAssistantSession } from '../src/assistant_session.ts';
import { openFakeModel } from './fake_model.ts';
import { startFakeModelServer, type ChatMessage, type FakeModelServer, type ModelStep } from './fake_model_server.ts';

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

async function runOneMessage(script: ModelStep[], customTools: Parameters<typeof createAssistantSession>[0]['customTools'] = []) {
  server = await startFakeModelServer(script);
  const { modelRuntime, model } = await openFakeModel(server.baseUrl, workDir);
  const session = await createAssistantSession({ modelRuntime, model, piDir: workDir, customTools });
  try {
    await session.prompt('Start.');
  } finally {
    session.dispose();
  }
  return server.requests;
}

function writeFiles(files: Record<string, string>): void {
  for (const [name, content] of Object.entries(files)) {
    const filePath = path.join(workDir, name);
    mkdirSync(path.dirname(filePath), { recursive: true });
    writeFileSync(filePath, content);
  }
}

function readToolResults(messages: ChatMessage[]): string[] {
  return messages.filter((message) => message.role === 'tool').map((message) => JSON.stringify(message.content));
}

describe('the assistant session', () => {
  test('runs no command when the model calls bash', async () => {
    const marker = path.join(workDir, 'bash-ran');

    const requests = await runOneMessage([
      { toolName: 'bash', toolArguments: { command: `touch ${marker}` } },
      { text: 'Done.' },
    ]);

    expect(existsSync(marker)).toBe(false);
    const results = readToolResults(requests[1]?.messages ?? []);
    expect(results).toHaveLength(1);
    expect(results[0]).toMatch(/Tool bash not found|is not an ATrade assistant tool/);
  });

  test('refuses a tool that is registered but is not in the tool list', async () => {
    const calls: unknown[] = [];
    const deleteStrategy = defineTool({
      name: 'delete_strategy',
      label: 'Delete strategy',
      description: 'Deletes a strategy.',
      parameters: Type.Object({ strategy_id: Type.String() }),
      execute: (_toolCallId, params) => {
        calls.push(params);
        return Promise.resolve({ content: [{ type: 'text', text: 'Deleted.' }], details: {} });
      },
    });

    const requests = await runOneMessage(
      [{ toolName: 'delete_strategy', toolArguments: { strategy_id: 's1' } }, { text: 'Done.' }],
      [deleteStrategy],
    );

    expect(calls).toEqual([]);
    expect(readToolResults(requests[1]?.messages ?? [])).toEqual([
      expect.stringContaining('delete_strategy is not an ATrade assistant tool.'),
    ]);
  });

  test('reads no AGENTS.md, no skill, and no extension at start', async () => {
    const extensionMarker = path.join(workDir, 'extension-ran');
    const extensionCode = `import { writeFileSync } from 'node:fs';
export default function (pi) {
  writeFileSync(${JSON.stringify(extensionMarker)}, 'ran');
  pi.registerTool({ name: 'extension_tool', label: 'x', description: 'x', parameters: {}, execute: async () => ({}) });
}
`;
    const skill = '---\nname: marker-skill\ndescription: SKILL-MARKER\n---\nSKILL-MARKER\n';
    writeFiles({
      'AGENTS.md': 'AGENTS-MARKER',
      'CLAUDE.md': 'AGENTS-MARKER',
      'SYSTEM.md': 'AGENTS-MARKER',
      '.pi/SYSTEM.md': 'AGENTS-MARKER',
      'skills/marker-skill/SKILL.md': skill,
      '.pi/skills/marker-skill/SKILL.md': skill,
      '.agents/skills/marker-skill/SKILL.md': skill,
      'extensions/marker.ts': extensionCode,
      '.pi/extensions/marker.ts': extensionCode,
      'settings.json': JSON.stringify({ extensions: ['extensions/marker.ts'], skills: ['skills'] }),
    });

    const requests = await runOneMessage([{ text: 'Hello.' }]);

    const sentText = JSON.stringify(requests[0]);
    expect(sentText).not.toContain('AGENTS-MARKER');
    expect(sentText).not.toContain('SKILL-MARKER');
    expect(existsSync(extensionMarker)).toBe(false);
    expect(requests[0]?.tools ?? []).toEqual([]);
  });

  test('sends no built-in pi tool to the model', async () => {
    const requests = await runOneMessage([{ text: 'Hello.' }]);

    expect(requests[0]?.tools ?? []).toEqual([]);
  });
});
