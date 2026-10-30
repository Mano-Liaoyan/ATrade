// Creates one pi agent session for the AI assistant (docs/architecture/assistant.md 25.2.1).
// - No built-in pi tool (noTools "builtin"). Only the custom tools of the caller.
// - The tool guard refuses each tool that is not in the tool list (the second guard).
// - pi reads no AGENTS.md, no skill, no prompt template, no theme, no extension file, and no settings file.
//   The tool guard is the only extension. It is code of this process, not a file that pi loads.
import {
  createAgentSession,
  DefaultResourceLoader,
  SessionManager,
  SettingsManager,
  type AgentSession,
  type ModelRuntime,
  type ToolDefinition,
} from '@earendil-works/pi-coding-agent';
import { ASSISTANT_TOOL_NAMES } from './assistant_tools.ts';
import { createToolGuard } from './tool_guard.ts';

export const SYSTEM_PROMPT = 'You are the ATrade strategy assistant.';

export interface AssistantSessionOptions {
  modelRuntime: ModelRuntime;
  model: NonNullable<Parameters<typeof createAgentSession>[0]>['model'];
  /** The directory of the pi files (the volume atrade-assistant-pi in the container). */
  piDir: string;
  customTools: ToolDefinition[];
  /** The session of one conversation (its JSONL file). Default: a session in memory. */
  conversationSession?: SessionManager;
}

async function createResourceLoader(piDir: string, settings: SettingsManager): Promise<DefaultResourceLoader> {
  const resourceLoader = new DefaultResourceLoader({
    cwd: piDir,
    agentDir: piDir,
    settingsManager: settings,
    noExtensions: true,
    noSkills: true,
    noPromptTemplates: true,
    noThemes: true,
    noContextFiles: true,
    systemPrompt: SYSTEM_PROMPT,
    extensionFactories: [{ name: 'atrade-tool-guard', factory: createToolGuard(ASSISTANT_TOOL_NAMES) }],
  });
  await resourceLoader.reload();
  return resourceLoader;
}

export async function createAssistantSession(options: AssistantSessionOptions): Promise<AgentSession> {
  const settings = SettingsManager.inMemory({ compaction: { enabled: false } });
  const { session } = await createAgentSession({
    cwd: options.piDir,
    agentDir: options.piDir,
    modelRuntime: options.modelRuntime,
    model: options.model,
    thinkingLevel: 'off',
    noTools: 'builtin',
    customTools: options.customTools,
    resourceLoader: await createResourceLoader(options.piDir, settings),
    sessionManager: options.conversationSession ?? SessionManager.inMemory(options.piDir),
    settingsManager: settings,
  });
  return session;
}
