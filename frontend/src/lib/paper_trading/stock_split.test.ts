import { describe, expect, it, vi } from 'vite-plus/test';
import { applyStockSplit, describeSplitCheck, keepLedger } from './stock_split';

describe('describeSplitCheck', () => {
  it('gives the ratio, the IBKR share counts, and the button text', () => {
    expect(
      describeSplitCheck({
        id: 7,
        stock_split_id: 3,
        split_ratio: '4',
        account_quantity_before: '10',
        account_quantity_after: '40',
      }),
    ).toEqual({ ratio: '4:1', shareCounts: '10 → 40', applyLabel: 'Apply split 4:1' });
  });
});

describe('applyStockSplit and keepLedger', () => {
  it('posts to the route of the split check', async () => {
    const fetchFunction = vi.fn(() => Promise.resolve(Response.json({}, { status: 200 })));

    await expect(applyStockSplit(fetchFunction, 7)).resolves.toEqual({ kind: 'done' });
    await expect(keepLedger(fetchFunction, 7)).resolves.toEqual({ kind: 'done' });

    expect(fetchFunction.mock.calls.map((call: unknown[]) => call[0])).toEqual([
      '/api/paper-trading/stock-splits/7/apply',
      '/api/paper-trading/stock-splits/7/keep-ledger',
    ]);
  });

  it('gives the detail of a refusal', async () => {
    const fetchFunction = vi.fn(() =>
      Promise.resolve(Response.json({ detail: 'AAPL is not in the Split check needed state.' }, { status: 409 })),
    );

    await expect(applyStockSplit(fetchFunction, 7)).resolves.toEqual({
      kind: 'failed',
      message: 'AAPL is not in the Split check needed state.',
    });
  });
});
