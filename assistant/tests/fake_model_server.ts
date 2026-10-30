// A local fake OpenAI-compatible model server (docs/architecture.md section 17.3). No real model provider in tests.
// Each answer is one step of a script: a text or a tool call. The server keeps each request body.
import { createServer, type IncomingMessage, type Server, type ServerResponse } from 'node:http';
import type { AddressInfo } from 'node:net';

export type ModelStep = { text: string } | { toolName: string; toolArguments: Record<string, unknown> };

export interface ChatMessage {
  role: string;
  content?: unknown;
  tool_call_id?: string;
}

export interface FakeModelServer {
  baseUrl: string;
  requests: { messages: ChatMessage[]; tools?: { function: { name: string } }[] }[];
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

function toChunks(step: ModelStep, stepNumber: number): unknown[] {
  if ('text' in step) {
    return [
      { delta: { role: 'assistant', content: step.text }, finish_reason: null },
      { delta: {}, finish_reason: 'stop' },
    ];
  }
  const toolCall = {
    index: 0,
    id: `call_${String(stepNumber)}`,
    type: 'function',
    function: { name: step.toolName, arguments: JSON.stringify(step.toolArguments) },
  };
  return [
    { delta: { role: 'assistant', tool_calls: [toolCall] }, finish_reason: null },
    { delta: {}, finish_reason: 'tool_calls' },
  ];
}

function writeStep(response: ServerResponse, step: ModelStep, stepNumber: number): void {
  response.writeHead(200, { 'content-type': 'text/event-stream' });
  for (const choice of toChunks(step, stepNumber)) {
    const chunk = { id: 'fake', object: 'chat.completion.chunk', created: 0, model: 'fake-model', choices: [choice] };
    response.write(`data: ${JSON.stringify({ ...chunk, choices: [{ index: 0, ...(choice as object) }] })}\n\n`);
  }
  response.end('data: [DONE]\n\n');
}

export async function startFakeModelServer(script: ModelStep[]): Promise<FakeModelServer> {
  const requests: FakeModelServer['requests'] = [];
  const server: Server = createServer((request, response) => {
    void readBody(request).then((body) => {
      requests.push(JSON.parse(body) as FakeModelServer['requests'][number]);
      const step = script[requests.length - 1] ?? { text: 'No more steps.' };
      writeStep(response, step, requests.length);
    });
  });
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
  const { port } = server.address() as AddressInfo;
  return {
    baseUrl: `http://127.0.0.1:${String(port)}/v1`,
    requests,
    close: () =>
      new Promise((resolve) => {
        server.closeAllConnections();
        server.close(() => {
          resolve();
        });
      }),
  };
}
