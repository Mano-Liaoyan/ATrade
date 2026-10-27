// Reads GET /api/ibkr/gateway and turns the answer into the IB Gateway status that the app shell shows.
import { describe, expect, it } from 'vitest';
import { describeGatewayStatus, fetchGatewayStatus } from './index';

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

describe('describeGatewayStatus', () => {
  it('says that IB Gateway is connected', () => {
    expect(describeGatewayStatus({ kind: 'connected' })).toBe('IB Gateway connected.');
  });

  it('says that IB Gateway is not reachable, where ATrade looks for it, and what to check', () => {
    expect(describeGatewayStatus({ kind: 'unreachable', address: 'ib-gateway:4004' })).toBe(
      'IB Gateway not reachable at ib-gateway:4004. ATrade keeps trying to connect. Make sure that the ib-gateway service runs and is logged in.',
    );
  });

  it('says that the Gateway status is not known when the backend does not answer', () => {
    expect(describeGatewayStatus({ kind: 'unknown' })).toBe('IB Gateway status not known.');
  });

  it('says that the check is running before the answer', () => {
    expect(describeGatewayStatus({ kind: 'checking' })).toBe('Checking IB Gateway.');
  });
});
