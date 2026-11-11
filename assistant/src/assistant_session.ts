// Creates one pi agent session for the AI assistant (docs/architecture/assistant.md 25.2.1).
// - No built-in pi tool (noTools "builtin"). Only the custom tools of the caller.
// - The tool guard refuses each tool that is not in the tool list (the second guard).
// - pi reads no AGENTS.md, no skill, no prompt template, no theme, no extension file, and no settings file.
//   The extensions are the tool guard and, when the caller gives it, the web tools (web_access.ts). Both are code
//   that this process imports, not files that pi loads.
import {
  createAgentSession,
  DefaultResourceLoader,
  SessionManager,
  SettingsManager,
  type AgentSession,
  type ExtensionFactory,
  type ModelRuntime,
  type ToolDefinition,
} from '@earendil-works/pi-coding-agent';
import { ASSISTANT_TOOL_NAMES } from './assistant_tools.ts';
import type { ThinkingLevel } from './model_selection.ts';
import { createToolGuard } from './tool_guard.ts';
import { REFUSED_WEB_ARGUMENTS, WEB_ACCESS_TOOL_NAMES } from './web_access.ts';

export interface AssistantSessionOptions {
  modelRuntime: ModelRuntime;
  model: NonNullable<Parameters<typeof createAgentSession>[0]>['model'];
  /** The thinking level of the run. pi lowers it to a level of the model (only "off" without reasoning). */
  thinkingLevel: ThinkingLevel;
  /** The directory of the pi files (the volume atrade-assistant-pi in the container). */
  piDir: string;
  customTools: ToolDefinition[];
  /** The system prompt of the conversation: the editable part and the fixed part (assistant.md 25.9). web makes it. */
  systemPrompt: string;
  /** The web tools (25.4.5). Default: the session has no web tool. */
  webAccess?: ExtensionFactory;
  /** The session of one conversation (its JSONL file). Default: a session in memory. */
  conversationSession?: SessionManager;
}

async function createResourceLoader(
  piDir: string,
  settings: SettingsManager,
  systemPrompt: string,
  webAccess: ExtensionFactory | undefined,
): Promise<DefaultResourceLoader> {
  const toolNames = webAccess === undefined ? ASSISTANT_TOOL_NAMES : [...ASSISTANT_TOOL_NAMES, ...WEB_ACCESS_TOOL_NAMES];
  const toolGuard = { name: 'atrade-tool-guard', factory: createToolGuard(toolNames, REFUSED_WEB_ARGUMENTS) };
  const resourceLoader = new DefaultResourceLoader({
    cwd: piDir,
    agentDir: piDir,
    settingsManager: settings,
    noExtensions: true,
    noSkills: true,
    noPromptTemplates: true,
    noThemes: true,
    noContextFiles: true,
    systemPrompt,
    extensionFactories: webAccess === undefined ? [toolGuard] : [toolGuard, { name: 'pi-web-access', factory: webAccess }],
  });
  await resourceLoader.reload();
  return resourceLoader;
}

export async function createAssistantSession(options: AssistantSessionOptions): Promise<AgentSession> {
  // The default settings: pi compacts the old messages into a summary before the context window is full (25.8.1).
  const settings = SettingsManager.inMemory();
  const { session } = await createAgentSession({
    cwd: options.piDir,
    agentDir: options.piDir,
    modelRuntime: options.modelRuntime,
    model: options.model,
    thinkingLevel: options.thinkingLevel,
    noTools: 'builtin',
    customTools: options.customTools,
    resourceLoader: await createResourceLoader(options.piDir, settings, options.systemPrompt, options.webAccess),
    sessionManager: options.conversationSession ?? SessionManager.inMemory(options.piDir),
    settingsManager: settings,
  });
  return session;
}
