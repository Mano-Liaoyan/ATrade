// Reads GET /api/health and turns the answer into a status that the app shell shows.
import { describe, expect, it } from 'vite-plus/test';
import { describeBackendHealth, fetchBackendHealth, readServerClock, type BackendHealth } from './index';

function respondWith(status: number, body: unknown): typeof fetch {
  return () => Promise.resolve(new Response(JSON.stringify(body), { status }));
}

describe('fetchBackendHealth', () => {
  it('reports ok with the server time when the database is reachable', async () => {
    const fetchHealth = respondWith(200, { status: 'ok', database: 'ok', time_utc: '2026-01-02T03:04:05Z' });

    const health = await fetchBackendHealth(fetchHealth, () => 1000);

    expect(health).toEqual({ kind: 'ok', serverTimeUtc: '2026-01-02T03:04:05Z', receivedAtMilliseconds: 1000 });
  });

  it('reports database unreachable when the backend answers 503', async () => {
    const fetchHealth = respondWith(503, { status: 'degraded', database: 'unreachable', time_utc: '2026-01-02T03:04:05Z' });

    const health = await fetchBackendHealth(fetchHealth);

    expect(health).toEqual({ kind: 'database_unreachable' });
  });

  it('reports backend unreachable when a proxy answers 502', async () => {
    const fetchHealth = respondWith(502, 'Bad Gateway');

    const health = await fetchBackendHealth(fetchHealth);

    expect(health).toEqual({ kind: 'backend_unreachable' });
  });

  it('reports backend unreachable when the request fails', async () => {
    const failingFetch: typeof fetch = () => Promise.reject(new TypeError('Failed to fetch'));

    const health = await fetchBackendHealth(failingFetch);

    expect(health).toEqual({ kind: 'backend_unreachable' });
  });
});

describe('readServerClock', () => {
  const healthAtFiveSeconds: BackendHealth = {
    kind: 'ok',
    serverTimeUtc: '2026-01-02T03:04:05.250Z',
    receivedAtMilliseconds: 5000,
  };

  it('shows the server time of day in UTC to the second', () => {
    expect(readServerClock(healthAtFiveSeconds, 5000)).toBe('03:04:05 UTC');
  });

  it('reads a server time with microseconds', () => {
    const health: BackendHealth = { ...healthAtFiveSeconds, serverTimeUtc: '2026-01-02T03:04:05.999999Z' };

    expect(readServerClock(health, 5000)).toBe('03:04:05 UTC');
  });

  it('adds the browser time since the answer to the server time', () => {
    expect(readServerClock(healthAtFiveSeconds, 67_000)).toBe('03:05:07 UTC');
  });

  it('has no server time when the backend did not answer', () => {
    expect(readServerClock({ kind: 'backend_unreachable' }, 0)).toBeNull();
    expect(readServerClock({ kind: 'database_unreachable' }, 0)).toBeNull();
    expect(readServerClock({ kind: 'checking' }, 0)).toBeNull();
  });
});

describe('describeBackendHealth', () => {
  it('says that the backend is connected', () => {
    const health: BackendHealth = { kind: 'ok', serverTimeUtc: '2026-01-02T03:04:05Z', receivedAtMilliseconds: 0 };

    expect(describeBackendHealth(health)).toEqual({ kind: 'success', text: 'Backend connected.' });
  });

  it('says that the database is not reachable', () => {
    expect(describeBackendHealth({ kind: 'database_unreachable' })).toEqual({
      kind: 'error',
      text: 'Backend connected. Database not reachable.',
    });
  });

  it('says that the backend is not reachable', () => {
    expect(describeBackendHealth({ kind: 'backend_unreachable' })).toEqual({
      kind: 'error',
      text: 'Backend not reachable.',
    });
  });

  it('says that the check is running before the answer', () => {
    expect(describeBackendHealth({ kind: 'checking' })).toEqual({ kind: 'in-progress', text: 'Checking the backend.' });
  });
});
