// Public entry of foundation/backend_health: reads GET /api/health for the app shell status line.
// The server time ticks in the browser: the server time of the answer plus the browser time since the answer.

import type { components } from '#lib/api';
import { formatUtcTime } from '#lib/foundation/time_format';

type HealthResponse = components['schemas']['HealthResponse'];

export type BackendHealth =
  | { kind: 'ok'; serverTimeUtc: string; receivedAtMilliseconds: number }
  | { kind: 'database_unreachable' }
  | { kind: 'backend_unreachable' }
  | { kind: 'checking' };

const HEALTH_PATH = '/api/health';
// The backend answers 503 when it cannot reach PostgreSQL. A proxy answers 502 or 504 when the backend is down.
const HTTP_SERVICE_UNAVAILABLE = 503;

// Python sends microseconds. Date.parse is sure to read only milliseconds in all browsers.
const MORE_THAN_MILLISECONDS_PATTERN = /(\.\d{3})\d+/;

// The app shell updates the server time this often.
export const SERVER_TIME_TICK_MILLISECONDS = 1000;

export async function fetchBackendHealth(
  fetchFunction: typeof fetch,
  readNowMilliseconds: () => number = Date.now,
): Promise<BackendHealth> {
  let response: Response;
  try {
    response = await fetchFunction(HEALTH_PATH);
  } catch {
    return { kind: 'backend_unreachable' };
  }
  if (response.status === HTTP_SERVICE_UNAVAILABLE) {
    return { kind: 'database_unreachable' };
  }
  if (!response.ok) {
    return { kind: 'backend_unreachable' };
  }
  const health = (await response.json()) as HealthResponse;
  return { kind: 'ok', serverTimeUtc: health.time_utc, receivedAtMilliseconds: readNowMilliseconds() };
}

/** `nowMilliseconds` is the browser time (Date.now()). Only the time since the answer comes from the browser clock. */
export function describeBackendHealth(health: BackendHealth, nowMilliseconds: number): string {
  switch (health.kind) {
    case 'ok': {
      const answerTimeMilliseconds = Date.parse(health.serverTimeUtc.replace(MORE_THAN_MILLISECONDS_PATTERN, '$1'));
      const serverTimeMilliseconds = answerTimeMilliseconds + nowMilliseconds - health.receivedAtMilliseconds;
      return `Backend connected. Server time ${formatUtcTime(new Date(serverTimeMilliseconds).toISOString())}.`;
    }
    case 'database_unreachable':
      return 'Backend connected. Database not reachable.';
    case 'backend_unreachable':
      return 'Backend not reachable.';
    case 'checking':
      return 'Checking the backend.';
  }
}
