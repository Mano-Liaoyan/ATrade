// The Connections button of the app shell header: one plug icon for the backend and IB Gateway.
import { describe, expect, it } from 'vite-plus/test';
import { summarizeConnections } from './header_connections';

const BACKEND_OK = { kind: 'ok', serverTimeUtc: '2026-01-02T03:04:05Z', receivedAtMilliseconds: 0 } as const;

describe('summarizeConnections', () => {
  it('shows no badge when the backend and IB Gateway are connected, and gives the server time in the backend row', () => {
    const connections = summarizeConnections(BACKEND_OK, { kind: 'connected' }, '03:04:05 UTC');

    expect(connections).toEqual({
      label: 'Connections',
      badge: null,
      rows: [
        { name: 'Backend', kind: 'success', stateLabel: 'Connected', detail: null, serverTime: '03:04:05 UTC' },
        { name: 'IB Gateway', kind: 'success', stateLabel: 'Connected', detail: null, serverTime: null },
      ],
    });
  });

  it('shows the error badge and what to check when IB Gateway is not reachable', () => {
    const connections = summarizeConnections(
      BACKEND_OK,
      { kind: 'unreachable', address: 'ib-gateway:4004' },
      '03:04:05 UTC',
    );

    expect(connections.badge).toBe('error');
    expect(connections.label).toBe('Connections: IB Gateway not reachable.');
    expect(connections.rows[1]).toEqual({
      name: 'IB Gateway',
      kind: 'error',
      stateLabel: 'Not reachable',
      detail:
        'Not reachable at ib-gateway:4004. ATrade keeps trying to connect. Make sure that the ib-gateway service runs and is logged in.',
      serverTime: null,
    });
  });

  // Without the backend, the IB Gateway status is not known: the backend gives it. A problem row says the problem.
  it('shows the error badge and no server time when the backend is not reachable', () => {
    const connections = summarizeConnections({ kind: 'backend_unreachable' }, { kind: 'unknown' }, null);

    expect(connections).toEqual({
      label: 'Connections: Backend not reachable. IB Gateway status not known.',
      badge: 'error',
      rows: [
        { name: 'Backend', kind: 'error', stateLabel: 'Not reachable', detail: 'Not reachable.', serverTime: null },
        { name: 'IB Gateway', kind: 'warning', stateLabel: 'Status not known', detail: 'Status not known.', serverTime: null },
      ],
    });
  });

  it('names the database when the backend answers but the database is not reachable', () => {
    const connections = summarizeConnections({ kind: 'database_unreachable' }, { kind: 'connected' }, null);

    expect(connections.badge).toBe('error');
    expect(connections.rows[0]).toEqual({
      name: 'Backend',
      kind: 'error',
      stateLabel: 'Database not reachable',
      detail: 'Database not reachable.',
      serverTime: null,
    });
  });

  it('shows the in-progress badge while the first checks run', () => {
    const connections = summarizeConnections({ kind: 'checking' }, { kind: 'checking' }, null);

    expect(connections.badge).toBe('in-progress');
    expect(connections.rows.map((row) => [row.kind, row.stateLabel])).toEqual([
      ['in-progress', 'Checking'],
      ['in-progress', 'Checking'],
    ]);
  });
});
