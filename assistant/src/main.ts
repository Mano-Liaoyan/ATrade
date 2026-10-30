// Entry point of the Compose service `assistant` (docs/architecture.md section 6.4). Node.js runs this file directly.
import { startAssistantServer } from './assistant_server.ts';
import { Conversations } from './conversations.ts';
import { openNoModel } from './model_selection.ts';

// The port of assistant in the network atrade-assistant-internal. Compose does not publish it.
const ASSISTANT_PORT = 8002;
// The volume atrade-assistant-pi (deploy/compose.yaml).
const PI_DIR = '/data';

// No credential exists until the credential store of #183. Each run then sends the error "The credential ... does not
// exist." The strategy and backtest tools come with #182.
const conversations = new Conversations({ piDir: PI_DIR, openModel: openNoModel, customTools: [] });
await startAssistantServer({ host: '0.0.0.0', port: ASSISTANT_PORT }, conversations);
console.log(`assistant listens on port ${String(ASSISTANT_PORT)}`);
