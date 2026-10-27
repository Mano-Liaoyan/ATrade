// Reads GET /api/health and turns the answer into a status that the app shell shows.
import { describe, expect, it } from 'vitest';
import { describeBackendHealth, fetchBackendHealth } from './index';

function respondWith(status: number, body: unknown): typeof fetch {
  return () => Promise.resolve(new Response(JSON.stringify(body), { status }));
}

describe('fetchBackendHealth', () => {
  it('reports ok with the server time when the database is reachable', async () => {
    const fetchHealth = respondWith(200, { status: 'ok', database: 'ok', time_utc: '2026-01-02T03:04:05Z' });

    const health = await fetchBackendHealth(fetchHealth);

    expect(health).toEqual({ kind: 'ok', serverTimeUtc: '2026-01-02T03:04:05Z' });
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

describe('describeBackendHealth', () => {
  it('names the server time in UTC', () => {
    expect(describeBackendHealth({ kind: 'ok', serverTimeUtc: '2026-01-02T03:04:05Z' })).toBe(
      'Backend connected. Server time 2026-01-02 03:04:05 UTC.',
    );
  });

  it('says that the database is not reachable', () => {
    expect(describeBackendHealth({ kind: 'database_unreachable' })).toBe('Backend connected. Database not reachable.');
  });

  it('says that the backend is not reachable', () => {
    expect(describeBackendHealth({ kind: 'backend_unreachable' })).toBe('Backend not reachable.');
  });

  it('says that the check is running before the answer', () => {
    expect(describeBackendHealth({ kind: 'checking' })).toBe('Checking the backend.');
  });
});
