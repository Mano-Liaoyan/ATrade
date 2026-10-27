// Public entry of foundation/backend_health: reads GET /api/health for the app shell status line.

// Hand-written until the OpenAPI type generation exists. It matches HealthResponse in backend/src/atrade/app/health_routes.py.
interface HealthResponse {
  status: 'ok' | 'degraded';
  database: 'ok' | 'unreachable';
  time_utc: string;
}

export type BackendHealth =
  | { kind: 'ok'; serverTimeUtc: string }
  | { kind: 'database_unreachable' }
  | { kind: 'backend_unreachable' }
  | { kind: 'checking' };

const HEALTH_PATH = '/api/health';
// The backend answers 503 when it cannot reach PostgreSQL. A proxy answers 502 or 504 when the backend is down.
const HTTP_SERVICE_UNAVAILABLE = 503;

export async function fetchBackendHealth(fetchFunction: typeof fetch): Promise<BackendHealth> {
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
  return { kind: 'ok', serverTimeUtc: health.time_utc };
}

export function describeBackendHealth(health: BackendHealth): string {
  switch (health.kind) {
    case 'ok': {
      const timeWithSpace = health.serverTimeUtc.replace('T', ' ');
      const readableTime = timeWithSpace.replace('Z', '');
      return `Backend connected. Server time ${readableTime} UTC.`;
    }
    case 'database_unreachable':
      return 'Backend connected. Database not reachable.';
    case 'backend_unreachable':
      return 'Backend not reachable.';
    case 'checking':
      return 'Checking the backend.';
  }
}
