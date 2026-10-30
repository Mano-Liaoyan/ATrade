// The allocated capital of the start dialog: the unallocated amount and the reason that blocks the start.
import { describe, expect, it } from 'vite-plus/test';
import { describeUnallocated, findCapitalBlockReason, readForwardTestCapital } from './forward_test_capital';

describe('readForwardTestCapital', () => {
  it('reads the capital of the paper account', async () => {
    const requests: string[] = [];
    const body = { net_liquidation_usd: '101234.50', allocated_usd: '39984.50', unallocated_usd: '61250.00' };
    const fetchFunction: typeof fetch = (input) => {
      requests.push(input as string);
      return Promise.resolve(new Response(JSON.stringify(body), { status: 200 }));
    };

    expect(await readForwardTestCapital(fetchFunction)).toEqual(body);
    expect(requests).toEqual(['/api/forward-tests/capital']);
  });

  it('gives null when the backend is not reachable', async () => {
    const fetchFunction: typeof fetch = () => Promise.reject(new TypeError('Failed to fetch'));

    expect(await readForwardTestCapital(fetchFunction)).toBeNull();
  });
});

describe('the unallocated amount', () => {
  it('shows the amount with thousands separators', () => {
    expect(describeUnallocated('61250')).toBe('Unallocated: 61,250.00 USD');
  });
});

describe('findCapitalBlockReason', () => {
  const unavailableReason = 'Paper account not checked. IB Gateway is not connected.';

  it('does not block a capital that is not larger than the unallocated amount', () => {
    expect(findCapitalBlockReason('61250.00', '61250.00', unavailableReason)).toBeNull();
    expect(findCapitalBlockReason('', '61250.00', unavailableReason)).toBeNull();
  });

  it('blocks a capital that is larger than the unallocated amount', () => {
    expect(findCapitalBlockReason(' 61250.01 ', '61250.00', unavailableReason)).toBe(
      'Capital is larger than the unallocated 61,250.00 USD',
    );
  });

  it('blocks the start with the given reason when the unallocated amount is not available', () => {
    expect(findCapitalBlockReason('1000', null, unavailableReason)).toBe(unavailableReason);
  });
});
