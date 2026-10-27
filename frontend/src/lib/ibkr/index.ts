// Public entry of ibkr: reads GET /api/ibkr/gateway for the IB Gateway status line of the app shell.

// Hand-written until the OpenAPI type generation exists. It matches GatewayStatusResponse in backend/src/atrade/ibkr/http_routes.py.
interface GatewayStatusResponse {
  status: 'connected' | 'unreachable';
  host: string;
  port: number;
}

export type GatewayStatus =
  | { kind: 'connected' }
  | { kind: 'unreachable'; address: string }
  | { kind: 'unknown' }
  | { kind: 'checking' };

const GATEWAY_STATUS_PATH = '/api/ibkr/gateway';
// The app shell reads the status again at this interval, because the backend connects again after a loss.
export const GATEWAY_STATUS_REFRESH_MILLISECONDS = 10_000;

export async function fetchGatewayStatus(fetchFunction: typeof fetch): Promise<GatewayStatus> {
  let response: Response;
  try {
    response = await fetchFunction(GATEWAY_STATUS_PATH);
  } catch {
    return { kind: 'unknown' };
  }
  if (!response.ok) {
    return { kind: 'unknown' };
  }
  const gatewayStatus = (await response.json()) as GatewayStatusResponse;
  if (gatewayStatus.status === 'connected') {
    return { kind: 'connected' };
  }
  return { kind: 'unreachable', address: `${gatewayStatus.host}:${String(gatewayStatus.port)}` };
}

export function describeGatewayStatus(gatewayStatus: GatewayStatus): string {
  switch (gatewayStatus.kind) {
    case 'connected':
      return 'IB Gateway connected.';
    case 'unreachable':
      return `IB Gateway not reachable at ${gatewayStatus.address}. ATrade keeps trying to connect. Make sure that the ib-gateway service runs and is logged in.`;
    case 'unknown':
      return 'IB Gateway status not known.';
    case 'checking':
      return 'Checking IB Gateway.';
  }
}
