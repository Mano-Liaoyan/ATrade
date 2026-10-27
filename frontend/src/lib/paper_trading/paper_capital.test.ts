// The default paper capital of the backtest form, from GET /api/paper-trading/paper-capital.
import { describe, expect, it } from 'vitest';
import { readPaperCapital } from './index';

describe('readPaperCapital', () => {
  it('returns the paper capital in USD', async () => {
    const answeringFetch: typeof fetch = () =>
      Promise.resolve(new Response(JSON.stringify({ paper_capital_usd: '101234.50' }), { status: 200 }));

    expect(await readPaperCapital(answeringFetch)).toBe('101234.50');
  });

  it('returns null when the backend is not reachable, so that the user types the amount', async () => {
    const failingFetch: typeof fetch = () => Promise.reject(new TypeError('Failed to fetch'));

    expect(await readPaperCapital(failingFetch)).toBeNull();
  });
});
