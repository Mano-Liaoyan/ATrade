// The source order choices of the backtest form and the read of the global source order.
import { describe, expect, it } from 'vite-plus/test';
import { formatBarSource, formatSourceOrder, listSourceOrders, readSourceOrder } from './source_order';

describe('listSourceOrders', () => {
  it('gives each order of the bar sources once, the given order first', () => {
    expect(listSourceOrders(['databento', 'ibkr'])).toEqual([
      ['databento', 'ibkr'],
      ['ibkr', 'databento'],
    ]);
  });
});

describe('formatSourceOrder', () => {
  it('names the bar sources in their order', () => {
    expect(formatSourceOrder(['ibkr', 'databento'])).toBe('IBKR, Databento');
    expect(formatBarSource('databento')).toBe('Databento');
  });
});

describe('readSourceOrder', () => {
  it('returns the global source order', async () => {
    const answeringFetch: typeof fetch = () =>
      Promise.resolve(new Response(JSON.stringify({ source_order: ['databento', 'ibkr'] }), { status: 200 }));

    expect(await readSourceOrder(answeringFetch)).toEqual({ kind: 'ok', value: ['databento', 'ibkr'] });
  });
});
