// Public entry of ibkr: reads GET /api/ibkr/gateway for the Connections button of the app shell.

import type { components } from '#lib/api';

type GatewayStatusResponse = components['schemas']['GatewayStatusResponse'];

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
