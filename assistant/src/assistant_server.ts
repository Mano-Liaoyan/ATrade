// The HTTP listener of the assistant service in the network atrade-assistant-internal (docs/architecture/assistant.md
// 25.14). Only web calls it. The browser never connects to it.
//
//   GET    /health                          The Compose health check.
//   POST   /conversations/{id}/runs         {text, provider, model, credential_id, system_prompt} → the run events as
//                                           JSON lines.
//   POST   /conversations/{id}/steer        {text} → 204, or 409 without an active run.
//   POST   /conversations/{id}/abort        → 204.
//   POST   /conversations/{id}/title        {provider, model, credential_id} → {title}, or 502 {detail}.
//   GET    /conversations/{id}/messages     → {messages}.
//   DELETE /conversations/{id}              Stops the active run and deletes the JSONL file → 204.
import { createServer, type IncomingMessage, type Server, type ServerResponse } from 'node:http';
import type { Conversations } from './conversations.ts';
import type { ModelSelection } from './model_selection.ts';

const HTTP_OK = 200;
const HTTP_NO_CONTENT = 204;
const HTTP_BAD_REQUEST = 400;
const HTTP_NOT_FOUND = 404;
const HTTP_CONFLICT = 409;
const HTTP_BAD_GATEWAY = 502;
// Only digits, so a conversation ID can never name a path outside the conversation directory.
const CONVERSATION_PATH = /^\/conversations\/(\d+)(?:\/(runs|steer|abort|title|messages))?$/u;

export interface ListenAddress {
  host: string;
  port: number;
}

class BadRequestError extends Error {}

type RouteAction = (conversationId: string, request: IncomingMessage, response: ServerResponse) => Promise<void>;

function sendJson(response: ServerResponse, status: number, body: unknown): void {
  response.writeHead(status, { 'content-type': 'application/json' });
  response.end(JSON.stringify(body));
}

function sendNoContent(response: ServerResponse): void {
  response.writeHead(HTTP_NO_CONTENT);
  response.end();
}

async function readJson(request: IncomingMessage): Promise<Record<string, unknown>> {
  const chunks: Buffer[] = [];
  for await (const chunk of request) {
    chunks.push(chunk as Buffer);
  }
  try {
    const body: unknown = JSON.parse(Buffer.concat(chunks).toString('utf8'));
    if (typeof body === 'object' && body !== null) {
      return body as Record<string, unknown>;
    }
  } catch {
    // The body is not JSON. The error below names the problem.
  }
  throw new BadRequestError('The body must be a JSON object.');
}

function readText(body: Record<string, unknown>, name: string): string {
  const value = body[name];
  if (typeof value !== 'string' || value === '') {
    throw new BadRequestError(`The field ${name} must be a text that is not empty.`);
  }
  return value;
}

function readSelection(body: Record<string, unknown>): ModelSelection {
  return {
    provider: readText(body, 'provider'),
    model: readText(body, 'model'),
    credentialId: readText(body, 'credential_id'),
  };
}

function createRoutes(conversations: Conversations): Record<string, RouteAction> {
  return {
    'POST runs': async (conversationId, request, response) => {
      const body = await readJson(request);
      const runRequest = {
        text: readText(body, 'text'),
        selection: readSelection(body),
        systemPrompt: readText(body, 'system_prompt'),
      };
      response.writeHead(HTTP_OK, { 'content-type': 'application/x-ndjson' });
      await conversations.run(conversationId, runRequest, (event) => {
        response.write(`${JSON.stringify(event)}\n`);
      });
      response.end();
    },
    'POST steer': async (conversationId, request, response) => {
      const text = readText(await readJson(request), 'text');
      if (await conversations.steer(conversationId, text)) {
        sendNoContent(response);
      } else {
        sendJson(response, HTTP_CONFLICT, { detail: 'The conversation has no active run.' });
      }
    },
    'POST abort': async (conversationId, _request, response) => {
      await conversations.abort(conversationId);
      sendNoContent(response);
    },
    'POST title': async (conversationId, request, response) => {
      const selection = readSelection(await readJson(request));
      try {
        sendJson(response, HTTP_OK, { title: await conversations.generateTitle(conversationId, selection) });
      } catch (error) {
        sendJson(response, HTTP_BAD_GATEWAY, { detail: error instanceof Error ? error.message : String(error) });
      }
    },
    'GET messages': (conversationId, _request, response) => {
      sendJson(response, HTTP_OK, { messages: conversations.readMessages(conversationId) });
      return Promise.resolve();
    },
    'DELETE ': async (conversationId, _request, response) => {
      await conversations.delete(conversationId);
      sendNoContent(response);
    },
  };
}

/** The conversation ID and the route action of a request, or undefined when no route matches. */
function findRoute(
  routes: Record<string, RouteAction>,
  request: IncomingMessage,
): { conversationId: string; action: RouteAction } | undefined {
  const [, conversationId, routeName = ''] = CONVERSATION_PATH.exec(request.url ?? '') ?? [];
  const action = routes[`${request.method ?? ''} ${routeName}`];
  if (conversationId === undefined || action === undefined) {
    return undefined;
  }
  return { conversationId, action };
}

async function answer(routes: Record<string, RouteAction>, request: IncomingMessage, response: ServerResponse) {
  if (request.method === 'GET' && request.url === '/health') {
    sendJson(response, HTTP_OK, { status: 'ok' });
    return;
  }
  const route = findRoute(routes, request);
  if (route === undefined) {
    sendJson(response, HTTP_NOT_FOUND, { detail: 'Not Found' });
    return;
  }
  try {
    await route.action(route.conversationId, request, response);
  } catch (error) {
    if (!(error instanceof BadRequestError)) {
      throw error;
    }
    sendJson(response, HTTP_BAD_REQUEST, { detail: error.message });
  }
}

export async function startAssistantServer(address: ListenAddress, conversations: Conversations): Promise<Server> {
  const routes = createRoutes(conversations);
  const server = createServer((request, response) => {
    answer(routes, request, response).catch((error: unknown) => {
      console.error(error);
      response.destroy();
    });
  });
  await new Promise<void>((resolve) => server.listen(address.port, address.host, resolve));
  return server;
}
