// The web tools of the AI assistant (docs/architecture/assistant.md 25.4.5): the pi extension pi-web-access.
// ATrade writes its settings file at each start and loads the extension from node_modules. pi loads no extension file.
import { writeFileSync } from 'node:fs';
import path from 'node:path';
import type { ExtensionFactory } from '@earendil-works/pi-coding-agent';

export const WEB_ACCESS_TOOL_NAMES: readonly string[] = ['web_search', 'fetch_content', 'get_search_content'];

/** The tool guard refuses a web tool call with one of these arguments: they send the request through a proxy of the
 * model, or with browser cookies. */
export const REFUSED_WEB_ARGUMENTS: readonly string[] = ['proxy', 'auth'];

// The file name that pi-web-access reads in the directory PI_CODING_AGENT_DIR.
const SETTINGS_FILE = 'web-search.json';
const DISABLED = { enabled: false };

/** Only the search and the fetch of public HTTP and HTTPS pages. No command, no browser, no clone, no local file. */
const WEB_ACCESS_SETTINGS = {
  // Each web tool is in the first model request. Without this, the extension adds the loader tool web_enable.
  toolActivation: 'eager',
  workflow: 'none',
  tools: { sourceCheck: DISABLED },
  commands: { websearch: DISABLED, curator: DISABLED, search: DISABLED, 'google-account': DISABLED },
  fetch: { allowedModes: ['readable', 'raw'] },
  allowBrowserCookies: false,
  autoOpenBrowser: false,
  githubClone: DISABLED,
  githubPrIssue: DISABLED,
  youtube: DISABLED,
  video: DISABLED,
};

/** Writes the settings file into the pi directory and loads the extension. Call it one time, at the process start:
 * the extension reads PI_CODING_AGENT_DIR one time, at its import. */
export async function loadWebAccess(piDir: string): Promise<ExtensionFactory> {
  writeFileSync(path.join(piDir, SETTINGS_FILE), JSON.stringify(WEB_ACCESS_SETTINGS));
  process.env.PI_CODING_AGENT_DIR = piDir;
  const extension = await import('pi-web-access/dist/index.js');
  return extension.default;
}
