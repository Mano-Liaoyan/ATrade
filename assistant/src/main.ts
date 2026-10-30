// Entry point of the Compose service `assistant` (docs/architecture.md section 6.4). Node.js runs this file directly.
import path from 'node:path';
import { startAssistantServer } from './assistant_server.ts';
import { createAssistantTools } from './assistant_tools.ts';
import { SERVICE_BACKTEST_WAIT } from './backtest_tools.ts';
import { Conversations } from './conversations.ts';
import { CredentialFile, createModelRuntime } from './credential_file.ts';
import { Logins } from './logins.ts';
import { openStoredModel } from './providers.ts';
import { WEB_PORT_URL, WebPortClient } from './web_port_client.ts';

// The port of assistant in the network atrade-assistant-internal. Compose does not publish it.
const ASSISTANT_PORT = 8002;
// The volume atrade-assistant-pi (deploy/compose.yaml).
const PI_DIR = '/data';
// The credential file (docs/architecture/assistant.md 25.7.2). Mode 0600.
const CREDENTIAL_FILE = path.join(PI_DIR, 'credentials.json');

const file = new CredentialFile(CREDENTIAL_FILE);
const logins = new Logins({ file, createRuntime: createModelRuntime });
// The tools call port 8001 of web with the conversation ID of the run.
const conversations = new Conversations({
  piDir: PI_DIR,
  openModel: openStoredModel(file, createModelRuntime),
  createTools: ({ conversationId, budget }) =>
    createAssistantTools({
      client: new WebPortClient(WEB_PORT_URL, conversationId),
      budget,
      wait: SERVICE_BACKTEST_WAIT,
    }),
});
await startAssistantServer({ host: '0.0.0.0', port: ASSISTANT_PORT }, conversations, {
  file,
  logins,
  createRuntime: createModelRuntime,
});
console.log(`assistant listens on port ${String(ASSISTANT_PORT)}`);
