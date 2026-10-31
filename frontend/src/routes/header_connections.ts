// The Connections button of the app shell header: one plug icon for the backend and for IB Gateway.
// The icon has no badge when both are connected. A problem adds the status badge of the worst status, and the button
// popover lists the backend and IB Gateway with their details. The server time is in the backend row.

import type { BackendHealth } from '#lib/foundation/backend_health';
import type { StatusKind } from '#lib/foundation/carbon';
import type { GatewayStatus } from '#lib/ibkr';

export interface ConnectionRow {
  name: 'Backend' | 'IB Gateway';
  kind: StatusKind;
  /** The accessible name of the status icon of the row. */
  stateLabel: string;
  /** The problem and what to check. Null for a connected or checked row: the status icon says all. */
  detail: string | null;
  /** The server clock, for example "03:04:05 UTC". Only the row of a connected backend has it. */
  serverTime: string | null;
}

export interface HeaderConnections {
  /** The accessible name and the tooltip of the button. */
  label: string;
  /** The status badge on the plug icon, or null when all connections are connected. */
  badge: StatusKind | null;
  rows: ConnectionRow[];
}

function createRow(name: ConnectionRow['name'], kind: StatusKind, stateLabel: string, detail: string | null = null): ConnectionRow {
  return { name, kind, stateLabel, detail, serverTime: null };
}

function describeBackendRow(health: BackendHealth, serverClock: string | null): ConnectionRow {
  switch (health.kind) {
    case 'ok':
      return { ...createRow('Backend', 'success', 'Connected'), serverTime: serverClock };
    case 'database_unreachable':
      return createRow('Backend', 'error', 'Database not reachable', 'Database not reachable.');
    case 'backend_unreachable':
      return createRow('Backend', 'error', 'Not reachable', 'Not reachable.');
    case 'checking':
      return createRow('Backend', 'in-progress', 'Checking');
  }
}

function describeGatewayRow(status: GatewayStatus): ConnectionRow {
  switch (status.kind) {
    case 'connected':
      return createRow('IB Gateway', 'success', 'Connected');
    case 'unreachable':
      return createRow(
        'IB Gateway',
        'error',
        'Not reachable',
        `Not reachable at ${status.address}. ATrade keeps trying to connect. Make sure that the ib-gateway service runs and is logged in.`,
      );
    case 'unknown':
      return createRow('IB Gateway', 'warning', 'Status not known', 'Status not known.');
    case 'checking':
      return createRow('IB Gateway', 'in-progress', 'Checking');
  }
}

// A higher rank is a worse status. The badge shows the worst status of the rows.
const STATUS_RANKS: Record<StatusKind, number> = { success: 0, neutral: 0, 'in-progress': 1, warning: 2, error: 3 };

function findWorstKind(rows: ConnectionRow[]): StatusKind {
  return rows.reduce<StatusKind>((worst, row) => (STATUS_RANKS[row.kind] > STATUS_RANKS[worst] ? row.kind : worst), 'success');
}

export function summarizeConnections(
  backendHealth: BackendHealth,
  gatewayStatus: GatewayStatus,
  serverClock: string | null,
): HeaderConnections {
  const rows = [describeBackendRow(backendHealth, serverClock), describeGatewayRow(gatewayStatus)];
  const problems = rows.filter((row) => row.kind !== 'success');
  if (problems.length === 0) {
    return { label: 'Connections', badge: null, rows };
  }
  const problemText = problems.map((row) => `${row.name} ${row.stateLabel.toLowerCase()}.`).join(' ');
  return { label: `Connections: ${problemText}`, badge: findWorstKind(rows), rows };
}
