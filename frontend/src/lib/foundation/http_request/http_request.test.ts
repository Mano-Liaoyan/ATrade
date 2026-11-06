// Sends HTTP requests to the backend and turns a failed answer into a message for the user.
import { describe, expect, it } from 'vite-plus/test';
import { BACKEND_NOT_REACHABLE, describeErrorBody, jsonRequest, readErrorMessage, requestJson, sendCommand, sendRequest } from './index';

function respondWith(status: number, body: unknown): typeof fetch {
  return () => Promise.resolve(new Response(JSON.stringify(body), { status }));
}

const failingFetch: typeof fetch = () => Promise.reject(new TypeError('Failed to fetch'));

describe('sendRequest', () => {
  it('returns the response of the backend', async () => {
    const response = await sendRequest(respondWith(404, { detail: 'Not found.' }), '/api/items/1');

    expect(response?.status).toBe(404);
  });

  it('returns null when the backend is not reachable', async () => {
    expect(await sendRequest(failingFetch, '/api/items')).toBeNull();
  });
});

describe('readErrorMessage', () => {
  it('returns the detail text of the backend', async () => {
    const response = new Response(JSON.stringify({ detail: 'A strategy with this name exists.' }), { status: 409 });

    expect(await readErrorMessage(response, 'The strategy request')).toBe('A strategy with this name exists.');
  });

  it('names the field and the reason of the first validation error', async () => {
    const detail = [
      { loc: ['body', 'paper_capital_usd'], msg: 'Input should be greater than 0', type: 'greater_than' },
      { loc: ['body', 'symbol'], msg: 'Field required', type: 'missing' },
    ];
    const response = new Response(JSON.stringify({ detail }), { status: 422 });

    expect(await readErrorMessage(response, 'The backtest request')).toBe('paper_capital_usd: Input should be greater than 0');
  });

  it('names the HTTP status when a proxy answers without JSON', async () => {
    const response = new Response('Bad Gateway', { status: 502 });

    expect(await readErrorMessage(response, 'Reading the bars')).toBe('Reading the bars failed with HTTP status 502.');
  });

  it('names the HTTP status when the JSON has no detail or an empty list', async () => {
    expect(await readErrorMessage(new Response('{}', { status: 500 }), 'The request')).toBe(
      'The request failed with HTTP status 500.',
    );
    expect(await readErrorMessage(new Response('{"detail": []}', { status: 422 }), 'The request')).toBe(
      'The request failed with HTTP status 422.',
    );
  });
});

describe('describeErrorBody', () => {
  it('describes a body that the capability already read', () => {
    expect(describeErrorBody({ detail: 'Wrong account.' }, 403, 'The order request')).toBe('Wrong account.');
    expect(describeErrorBody(null, 504, 'The order request')).toBe('The order request failed with HTTP status 504.');
  });
});

describe('requestJson', () => {
  it('returns the JSON body of a successful answer', async () => {
    const result = await requestJson<{ id: number }>(respondWith(200, { id: 3 }), 'The item request', '/api/items/3');

    expect(result).toEqual({ kind: 'ok', value: { id: 3 } });
  });

  it('returns the error message of a failed answer', async () => {
    const result = await requestJson(respondWith(404, { detail: 'Item not found.' }), 'The item request', '/api/items/3');

    expect(result).toEqual({ kind: 'failed', message: 'Item not found.' });
  });

  it('says that the backend is not reachable', async () => {
    const result = await requestJson(failingFetch, 'The item request', '/api/items');

    expect(result).toEqual({ kind: 'failed', message: BACKEND_NOT_REACHABLE });
    expect(BACKEND_NOT_REACHABLE).toBe('The backend is not reachable.');
  });
});

describe('sendCommand', () => {
  it('does not read the empty body of an accepted command', async () => {
    const accepted: typeof fetch = () => Promise.resolve(new Response(null, { status: 204 }));

    expect(await sendCommand(accepted, 'The item request', '/api/items/3', { method: 'DELETE' })).toEqual({ kind: 'ok', value: undefined });
  });

  it('returns the error message of a refused command', async () => {
    const result = await sendCommand(respondWith(409, { detail: 'Item in use.' }), 'The item request', '/api/items/3');

    expect(result).toEqual({ kind: 'failed', message: 'Item in use.' });
  });

  it('says that the backend is not reachable', async () => {
    expect(await sendCommand(failingFetch, 'The item request', '/api/items/3')).toEqual({ kind: 'failed', message: BACKEND_NOT_REACHABLE });
  });
});

describe('jsonRequest', () => {
  it('writes the method, the JSON header, and the body', () => {
    expect(jsonRequest('PUT', { id: 3 })).toEqual({ method: 'PUT', headers: { 'content-type': 'application/json' }, body: '{"id":3}' });
  });
});
