import { buildApiUrl } from './apiBaseUrl';
import type { BrokerStatus } from '../types/brokerStatus';

export async function getBrokerStatus(): Promise<BrokerStatus> {
  const response = await fetch(buildApiUrl('/api/broker/ibkr/status'), {
    cache: 'no-store',
    headers: {
      Accept: 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Broker status request failed with HTTP ${response.status}.`);
  }

  return response.json() as Promise<BrokerStatus>;
}
