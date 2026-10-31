// Reads GET /api/ibkr/gateway and turns the answer into the IB Gateway status that the app shell shows.
import { describe, expect, it } from 'vite-plus/test';
import { fetchGatewayStatus } from './index';

function respondWith(status: number, body: unknown): typeof fetch {
  return () => Promise.resolve(new Response(JSON.stringify(body), { status }));
}

describe('fetchGatewayStatus', () => {
  it('reports connected when the Web process is connected to IB Gateway', async () => {
    const fetchStatus = respondWith(200, { status: 'connected', host: 'ib-gateway', port: 4004 });

    const gatewayStatus = await fetchGatewayStatus(fetchStatus);

    expect(gatewayStatus).toEqual({ kind: 'connected' });
  });

  it('reports unreachable with the Gateway address', async () => {
    const fetchStatus = respondWith(200, { status: 'unreachable', host: 'ib-gateway', port: 4004 });

    const gatewayStatus = await fetchGatewayStatus(fetchStatus);

    expect(gatewayStatus).toEqual({ kind: 'unreachable', address: 'ib-gateway:4004' });
  });

  it('reports unknown when the backend does not answer', async () => {
    const failingFetch: typeof fetch = () => Promise.reject(new TypeError('Failed to fetch'));

    const gatewayStatus = await fetchGatewayStatus(failingFetch);

    expect(gatewayStatus).toEqual({ kind: 'unknown' });
  });

  it('reports unknown when a proxy answers 502', async () => {
    const gatewayStatus = await fetchGatewayStatus(respondWith(502, 'Bad Gateway'));

    expect(gatewayStatus).toEqual({ kind: 'unknown' });
  });
});
