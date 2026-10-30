// The HTTP listener of the assistant service in the network atrade-assistant-internal.
// In this stage it has only GET /health for the Compose health check. The protocol between web and assistant
// comes later (docs/architecture/assistant.md 25.14).
import { createServer, type Server } from 'node:http';

const HTTP_OK = 200;
const HTTP_NOT_FOUND = 404;

export interface ListenAddress {
  host: string;
  port: number;
}

export async function startHealthServer(address: ListenAddress): Promise<Server> {
  const server = createServer((request, response) => {
    const isHealth = request.method === 'GET' && request.url === '/health';
    response.writeHead(isHealth ? HTTP_OK : HTTP_NOT_FOUND, { 'content-type': 'application/json' });
    response.end(JSON.stringify(isHealth ? { status: 'ok' } : { detail: 'Not Found' }));
  });
  await new Promise<void>((resolve) => server.listen(address.port, address.host, resolve));
  return server;
}
