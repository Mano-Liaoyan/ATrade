// Entry point of the Compose service `assistant` (docs/architecture.md section 6.4). Node.js runs this file directly.
import { startHealthServer } from './health_server.ts';

// The port of assistant in the network atrade-assistant-internal. Compose does not publish it.
const ASSISTANT_PORT = 8002;

await startHealthServer({ host: '0.0.0.0', port: ASSISTANT_PORT });
console.log(`assistant listens on port ${String(ASSISTANT_PORT)}`);
