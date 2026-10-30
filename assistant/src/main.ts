// Entry point of the Compose service `assistant` (docs/architecture.md section 6.4). Node.js runs this file directly.
import path from 'node:path';
import { startAssistantServer } from './assistant_server.ts';
import { Conversations } from './conversations.ts';
import { CredentialFile, createModelRuntime } from './credential_file.ts';
import { Logins } from './logins.ts';
import { openStoredModel } from './providers.ts';

// The port of assistant in the network atrade-assistant-internal. Compose does not publish it.
const ASSISTANT_PORT = 8002;
// The volume atrade-assistant-pi (deploy/compose.yaml).
const PI_DIR = '/data';
// The credential file (docs/architecture/assistant.md 25.7.2). Mode 0600.
const CREDENTIAL_FILE = path.join(PI_DIR, 'credentials.json');

const file = new CredentialFile(CREDENTIAL_FILE);
const logins = new Logins({ file, createRuntime: createModelRuntime });
// The strategy and backtest tools come with #182.
const conversations = new Conversations({
  piDir: PI_DIR,
  openModel: openStoredModel(file, createModelRuntime),
  customTools: [],
});
await startAssistantServer({ host: '0.0.0.0', port: ASSISTANT_PORT }, conversations, {
  file,
  logins,
  createRuntime: createModelRuntime,
});
console.log(`assistant listens on port ${String(ASSISTANT_PORT)}`);
