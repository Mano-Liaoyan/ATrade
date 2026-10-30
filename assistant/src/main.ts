// Entry point of the Compose service `assistant` (docs/architecture.md section 6.4). Node.js runs this file directly.
import { startAssistantServer } from './assistant_server.ts';
import { createAssistantTools } from './assistant_tools.ts';
import { SERVICE_BACKTEST_WAIT } from './backtest_tools.ts';
import { Conversations } from './conversations.ts';
import { openNoModel } from './model_selection.ts';
import { WEB_PORT_URL, WebPortClient } from './web_port_client.ts';

// The port of assistant in the network atrade-assistant-internal. Compose does not publish it.
const ASSISTANT_PORT = 8002;
// The volume atrade-assistant-pi (deploy/compose.yaml).
const PI_DIR = '/data';

// No credential exists until the credential store of #183. Each run then sends the error "The credential ... does not
// exist." The tools call port 8001 of web with the conversation ID of the run.
const conversations = new Conversations({
  piDir: PI_DIR,
  openModel: openNoModel,
  createTools: ({ conversationId, budget }) =>
    createAssistantTools({
      client: new WebPortClient(WEB_PORT_URL, conversationId),
      budget,
      wait: SERVICE_BACKTEST_WAIT,
    }),
});
await startAssistantServer({ host: '0.0.0.0', port: ASSISTANT_PORT }, conversations);
console.log(`assistant listens on port ${String(ASSISTANT_PORT)}`);
