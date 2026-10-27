// Calls the strategy HTTP routes and turns each answer into a result that the editor page can show.
import { describe, expect, it } from 'vitest';
import { createStrategy, deleteStrategy, saveStrategyVersion } from './index';

const VERSION = {
  id: 7,
  strategy_id: 4,
  version_number: 3,
  code: 'x = 1\n',
  code_sha256: 'abc',
  created_at_utc: '2026-01-02T03:04:05Z',
};

function respondWith(status: number, body: unknown): typeof fetch {
  return () => Promise.resolve(new Response(JSON.stringify(body), { status }));
}

describe('saveStrategyVersion', () => {
  it('reports a new version when the backend answers 201', async () => {
    const result = await saveStrategyVersion(respondWith(201, VERSION), 4, 'x = 1\n');

    expect(result).toEqual({ kind: 'saved', version: VERSION, isNewVersion: true });
  });

  it('reports no new version when the code is the same as the latest version', async () => {
    const result = await saveStrategyVersion(respondWith(200, VERSION), 4, 'x = 1\n');

    expect(result).toEqual({ kind: 'saved', version: VERSION, isNewVersion: false });
  });

  it('returns the line and the reason of each failed check', async () => {
    const problems = [{ line: 2, message: 'F821 Undefined name `y`' }];

    const result = await saveStrategyVersion(respondWith(422, { problems }), 4, 'x = y\n');

    expect(result).toEqual({ kind: 'check_failed', problems });
  });

  it('reports a failure when the backend is not reachable', async () => {
    const failingFetch: typeof fetch = () => Promise.reject(new TypeError('Failed to fetch'));

    const result = await saveStrategyVersion(failingFetch, 4, 'x = 1\n');

    expect(result).toEqual({ kind: 'failed', message: 'The backend is not reachable.' });
  });
});

describe('createStrategy', () => {
  it('reports that the name is in use when the backend answers 409', async () => {
    const result = await createStrategy(respondWith(409, { detail: 'A strategy with this name exists.' }), 'Moving average');

    expect(result).toEqual({ kind: 'failed', message: 'A strategy with this name exists.' });
  });
});

describe('deleteStrategy', () => {
  it('reports that a strategy in use cannot be deleted', async () => {
    const detail = 'A backtest or forward test uses a version of this strategy. It cannot be deleted.';

    const result = await deleteStrategy(respondWith(409, { detail }), 4);

    expect(result).toEqual({ kind: 'failed', message: detail });
  });

  it('reports success when the backend answers 204', async () => {
    const noContent: typeof fetch = () => Promise.resolve(new Response(null, { status: 204 }));

    const result = await deleteStrategy(noContent, 4);

    expect(result).toEqual({ kind: 'deleted' });
  });

  it('names the HTTP status when a proxy answers without a message', async () => {
    const proxyFetch: typeof fetch = () => Promise.resolve(new Response('Bad Gateway', { status: 502 }));

    const result = await deleteStrategy(proxyFetch, 4);

    expect(result).toEqual({ kind: 'failed', message: 'The strategy request failed with HTTP status 502.' });
  });
});
