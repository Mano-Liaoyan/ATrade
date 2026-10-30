// A local fake OpenAI-compatible model server (docs/architecture.md section 17.3). No real model provider in tests.
// Each answer is one step of a script: a text or a tool call. The server keeps each request body.
// A text step with `holdUntil` sends its first half, then waits for the promise, then sends the rest. A test uses it to
// steer or abort a run while the model writes.
import { createServer, type IncomingMessage, type Server, type ServerResponse } from 'node:http';
import type { AddressInfo } from 'node:net';

export type ModelStep =
  | { text: string; holdUntil?: Promise<void> }
  | { toolName: string; toolArguments: Record<string, unknown> }
  | { status: number; body: string };

export interface ChatMessage {
  role: string;
  content?: unknown;
  tool_call_id?: string;
}

export interface FakeModelServer {
  baseUrl: string;
  requests: { model: string; messages: ChatMessage[]; tools?: { function: { name: string } }[] }[];
  /** Resolves when the server has received `count` requests. */
  waitForRequests: (count: number) => Promise<void>;
  close: () => Promise<void>;
}

function readBody(request: IncomingMessage): Promise<string> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    request.on('data', (chunk: Buffer) => chunks.push(chunk));
    request.on('end', () => {
      resolve(Buffer.concat(chunks).toString('utf8'));
    });
    request.on('error', reject);
  });
}

function toTextChunks(text: string): unknown[] {
  return [
    { delta: { role: 'assistant', content: text }, finish_reason: null },
    { delta: {}, finish_reason: 'stop' },
  ];
}

function toToolCallChunks(toolName: string, toolArguments: Record<string, unknown>, stepNumber: number): unknown[] {
  const toolCall = {
    index: 0,
    id: `call_${String(stepNumber)}`,
    type: 'function',
    function: { name: toolName, arguments: JSON.stringify(toolArguments) },
  };
  return [
    { delta: { role: 'assistant', tool_calls: [toolCall] }, finish_reason: null },
    { delta: {}, finish_reason: 'tool_calls' },
  ];
}

function writeChunk(response: ServerResponse, choice: unknown): void {
  const chunk = { id: 'fake', object: 'chat.completion.chunk', created: 0, model: 'fake-model' };
  response.write(`data: ${JSON.stringify({ ...chunk, choices: [{ index: 0, ...(choice as object) }] })}\n\n`);
}

async function writeStep(response: ServerResponse, step: ModelStep, stepNumber: number): Promise<void> {
  if ('status' in step) {
    response.writeHead(step.status, { 'content-type': 'application/json' });
    response.end(step.body);
    return;
  }
  response.writeHead(200, { 'content-type': 'text/event-stream' });
  if ('toolName' in step) {
    toToolCallChunks(step.toolName, step.toolArguments, stepNumber).forEach((choice) => {
      writeChunk(response, choice);
    });
    response.end('data: [DONE]\n\n');
    return;
  }
  if (step.holdUntil !== undefined) {
    const half = Math.ceil(step.text.length / 2);
    writeChunk(response, { delta: { role: 'assistant', content: step.text.slice(0, half) }, finish_reason: null });
    await step.holdUntil;
    toTextChunks(step.text.slice(half)).forEach((choice) => {
      writeChunk(response, choice);
    });
  } else {
    toTextChunks(step.text).forEach((choice) => {
      writeChunk(response, choice);
    });
  }
  response.end('data: [DONE]\n\n');
}

export async function startFakeModelServer(script: ModelStep[]): Promise<FakeModelServer> {
  const requests: FakeModelServer['requests'] = [];
  const waiters: { count: number; resolve: () => void }[] = [];
  const server: Server = createServer((request, response) => {
    void readBody(request).then(async (body) => {
      requests.push(JSON.parse(body) as FakeModelServer['requests'][number]);
      waiters.filter((waiter) => requests.length >= waiter.count).forEach((waiter) => {
        waiter.resolve();
      });
      const step = script[requests.length - 1] ?? { text: 'No more steps.' };
      await writeStep(response, step, requests.length);
    });
  });
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
  const { port } = server.address() as AddressInfo;
  return {
    baseUrl: `http://127.0.0.1:${String(port)}/v1`,
    requests,
    waitForRequests: (count) =>
      new Promise((resolve) => {
        if (requests.length >= count) {
          resolve();
          return;
        }
        waiters.push({ count, resolve });
      }),
    close: () =>
      new Promise((resolve) => {
        server.closeAllConnections();
        server.close(() => {
          resolve();
        });
      }),
  };
}
