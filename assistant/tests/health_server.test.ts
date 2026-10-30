// The Compose health check of the assistant service calls GET /health.
import type { AddressInfo } from 'node:net';
import { afterEach, expect, test } from 'vite-plus/test';
import { startHealthServer } from '../src/health_server.ts';

let close: (() => Promise<void>) | undefined;

afterEach(async () => {
  await close?.();
});

async function startOnFreePort(): Promise<string> {
  const server = await startHealthServer({ host: '127.0.0.1', port: 0 });
  close = () =>
    new Promise((resolve) => {
      server.close(() => {
        resolve();
      });
    });
  const { port } = server.address() as AddressInfo;
  return `http://127.0.0.1:${String(port)}`;
}

test('GET /health answers 200 with status ok', async () => {
  const baseUrl = await startOnFreePort();

  const response = await fetch(`${baseUrl}/health`);

  expect(response.status).toBe(200);
  expect(await response.json()).toEqual({ status: 'ok' });
});

test('another path answers 404', async () => {
  const baseUrl = await startOnFreePort();

  const response = await fetch(`${baseUrl}/conversations`);

  expect(response.status).toBe(404);
});
