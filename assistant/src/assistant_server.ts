// The HTTP listener of the assistant service in the network atrade-assistant-internal (docs/architecture/assistant.md
// 25.14). Only web calls it. The browser never connects to it.
//
//   GET    /health                          The Compose health check.
//   POST   /conversations/{id}/runs         {text, provider, model, credential_id, thinking_level, system_prompt} → the
//                                           run events as JSON lines.
//   POST   /conversations/{id}/steer        {text} → 204, or 409 without an active run.
//   POST   /conversations/{id}/abort        → 204.
//   POST   /conversations/{id}/title        {provider, model, credential_id} → {title}, or 502 {detail}.
//   GET    /conversations/{id}/messages     → {messages}.
//   DELETE /conversations/{id}              Stops the active run and deletes the JSONL file → 204.
//   GET    /providers                       → {providers} (25.7.1).
//   GET    /credentials                     → {credentials}, without secrets (25.7.4).
//   DELETE /credentials/{id}                → 204, or 404.
//   POST   /logins                          {provider, method, name} → the login events as JSON lines (25.7.3).
//                                           The login stops when web closes the request.
//   POST   /login-answers                   {prompt_id, value} → 204, or 404 when no login waits for the prompt.
import { createServer, type IncomingMessage, type Server, type ServerResponse } from 'node:http';
import type { Conversations } from './conversations.ts';
import type { CreateModelRuntime, CredentialFile } from './credential_file.ts';
import type { LoginMethod, Logins } from './logins.ts';
import { isThinkingLevel, THINKING_LEVELS, type ModelSelection, type ThinkingLevel } from './model_selection.ts';
import { listProviders } from './providers.ts';

const HTTP_OK = 200;
const HTTP_NO_CONTENT = 204;
const HTTP_BAD_REQUEST = 400;
const HTTP_NOT_FOUND = 404;
const HTTP_CONFLICT = 409;
const HTTP_BAD_GATEWAY = 502;
// Only digits, so a conversation ID can never name a path outside the conversation directory.
const CONVERSATION_PATH = /^\/conversations\/(\d+)(?:\/(runs|steer|abort|title|messages))?$/u;

const CREDENTIAL_PATH = /^\/credentials\/([\w-]+)$/u;
const LOGIN_METHODS: readonly string[] = ['oauth', 'api_key'];

/** The credential file, the logins, and the model runtime factory of the service (25.7). */
export interface CredentialServices {
  file: CredentialFile;
  logins: Logins;
  createRuntime: CreateModelRuntime;
}

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

function readThinkingLevel(body: Record<string, unknown>): ThinkingLevel {
  const value = body['thinking_level'];
  if (!isThinkingLevel(value)) {
    throw new BadRequestError(`The field thinking_level must be one of ${THINKING_LEVELS.join(', ')}.`);
  }
  return value;
}

function createRoutes(conversations: Conversations): Record<string, RouteAction> {
  return {
    'POST runs': async (conversationId, request, response) => {
      const body = await readJson(request);
      const runRequest = {
        text: readText(body, 'text'),
        selection: readSelection(body),
        thinkingLevel: readThinkingLevel(body),
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

function readLoginMethod(body: Record<string, unknown>): LoginMethod {
  const method = readText(body, 'method');
  if (!LOGIN_METHODS.includes(method)) {
    throw new BadRequestError('The field method must be oauth or api_key.');
  }
  return method as LoginMethod;
}

type PlainRouteAction = (request: IncomingMessage, response: ServerResponse) => Promise<void>;

function createCredentialRoutes(services: CredentialServices): Record<string, PlainRouteAction> {
  return {
    'GET /providers': async (_request, response) => {
      sendJson(response, HTTP_OK, { providers: await listProviders(services.file, services.createRuntime) });
    },
    'GET /credentials': (_request, response) => {
      sendJson(response, HTTP_OK, { credentials: services.file.list() });
      return Promise.resolve();
    },
    'POST /logins': async (request, response) => {
      const body = await readJson(request);
      const loginRequest = { provider: readText(body, 'provider'), method: readLoginMethod(body), name: readText(body, 'name') };
      const controller = new AbortController();
      response.on('close', () => {
        controller.abort();
      });
      response.writeHead(HTTP_OK, { 'content-type': 'application/x-ndjson' });
      await services.logins.login(
        loginRequest,
        (event) => {
          response.write(`${JSON.stringify(event)}\n`);
        },
        controller.signal,
      );
      response.end();
    },
    'POST /login-answers': async (request, response) => {
      const body = await readJson(request);
      const value = body.value;
      if (typeof value !== 'string') {
        throw new BadRequestError('The field value must be a text.');
      }
      if (services.logins.answer(readText(body, 'prompt_id'), value)) {
        sendNoContent(response);
      } else {
        sendJson(response, HTTP_NOT_FOUND, { detail: 'No login waits for this prompt.' });
      }
    },
  };
}

function findCredentialRoute(
  routes: Record<string, PlainRouteAction>,
  services: CredentialServices,
  request: IncomingMessage,
): PlainRouteAction | undefined {
  const credentialId = CREDENTIAL_PATH.exec(request.url ?? '')?.[1];
  if (request.method === 'DELETE' && credentialId !== undefined) {
    return (_request, response) => {
      if (services.file.delete(credentialId)) {
        sendNoContent(response);
      } else {
        sendJson(response, HTTP_NOT_FOUND, { detail: `The credential ${credentialId} does not exist.` });
      }
      return Promise.resolve();
    };
  }
  return routes[`${request.method ?? ''} ${request.url ?? ''}`];
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

interface ServerRoutes {
  conversations: Record<string, RouteAction>;
  credentials: Record<string, PlainRouteAction>;
  services: CredentialServices;
}

function findAnyRoute(routes: ServerRoutes, request: IncomingMessage): PlainRouteAction | undefined {
  if (request.method === 'GET' && request.url === '/health') {
    return (_request, response) => {
      sendJson(response, HTTP_OK, { status: 'ok' });
      return Promise.resolve();
    };
  }
  const route = findRoute(routes.conversations, request);
  if (route !== undefined) {
    return (routeRequest, response) => route.action(route.conversationId, routeRequest, response);
  }
  return findCredentialRoute(routes.credentials, routes.services, request);
}

async function answer(routes: ServerRoutes, request: IncomingMessage, response: ServerResponse) {
  const action = findAnyRoute(routes, request);
  if (action === undefined) {
    sendJson(response, HTTP_NOT_FOUND, { detail: 'Not Found' });
    return;
  }
  try {
    await action(request, response);
  } catch (error) {
    if (!(error instanceof BadRequestError)) {
      throw error;
    }
    sendJson(response, HTTP_BAD_REQUEST, { detail: error.message });
  }
}

export async function startAssistantServer(
  address: ListenAddress,
  conversations: Conversations,
  services: CredentialServices,
): Promise<Server> {
  const routes = { conversations: createRoutes(conversations), credentials: createCredentialRoutes(services), services };
  const server = createServer((request, response) => {
    answer(routes, request, response).catch((error: unknown) => {
      console.error(error);
      response.destroy();
    });
  });
  await new Promise<void>((resolve) => server.listen(address.port, address.host, resolve));
  return server;
}
