// Public entry of ibkr: reads GET /api/ibkr/gateway for the IB Gateway status icon of the app shell.

import type { components } from '#lib/api';
import type { StatusKind } from '#lib/foundation/carbon';

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

/** The status icon kind and the tooltip text of the IB Gateway status in the header. */
export interface GatewayStatusDescription {
  kind: StatusKind;
  text: string;
}

export function describeGatewayStatus(gatewayStatus: GatewayStatus): GatewayStatusDescription {
  switch (gatewayStatus.kind) {
    case 'connected':
      return { kind: 'success', text: 'IB Gateway connected.' };
    case 'unreachable':
      return {
        kind: 'error',
        text: `IB Gateway not reachable at ${gatewayStatus.address}. ATrade keeps trying to connect. Make sure that the ib-gateway service runs and is logged in.`,
      };
    case 'unknown':
      return { kind: 'warning', text: 'IB Gateway status not known.' };
    case 'checking':
      return { kind: 'in-progress', text: 'Checking IB Gateway.' };
  }
}
