// The key metric row of a test: one set of metrics in one order with one sign rule on all pages (spec #99).
import { describe, expect, it } from 'vite-plus/test';
import { readKeyMetrics, type TestTrade } from './index';

const METRICS = {
  final_equity_usd: '112345.6',
  total_return_percent: '12.3456',
  max_drawdown_percent: '37.71',
  trade_count: 4,
};

function trade(side: 'BUY' | 'SELL', quantity: string, price: string, commission = '1'): TestTrade {
  return { time_utc: '2024-01-02T00:00:00Z', side, quantity_shares: quantity, price_usd: price, commission_usd: commission };
}

describe('readKeyMetrics', () => {
  it('gives the metrics in one order with names and signed texts', () => {
    const tiles = readKeyMetrics({ metrics: METRICS, startCapitalUsd: '100000', trades: [] });

    expect(tiles.map((tile) => [tile.name, tile.text])).toEqual([
      ['Total return', '+12.35 %'],
      ['Net profit (USD)', '+12,345.60'],
      ['Max drawdown', '-37.71 %'],
      ['Win rate', '–'],
      ['Trades', '4'],
      ['Final equity (USD)', '112,345.60'],
    ]);
  });

  it('gives the direction of the return, the profit, and the drawdown', () => {
    const tiles = readKeyMetrics({
      metrics: { ...METRICS, final_equity_usd: '90000', total_return_percent: '-10' },
      startCapitalUsd: '100000',
      trades: [],
    });

    expect(tiles.map((tile) => tile.change)).toEqual([-10, -10000, -37.71, undefined, undefined, undefined]);
  });

  it('shows a max drawdown of 0 without a sign', () => {
    const tiles = readKeyMetrics({ metrics: { ...METRICS, max_drawdown_percent: '0' }, startCapitalUsd: '1', trades: [] });

    expect(tiles[2]).toEqual({ name: 'Max drawdown', text: '0.00 %', change: 0 });
  });

  it('shows a dash for the net profit when the start capital is not known', () => {
    const tiles = readKeyMetrics({ metrics: METRICS, startCapitalUsd: null, trades: [] });

    expect(tiles[1]).toEqual({ name: 'Net profit (USD)', text: '–', change: null });
  });

  it('computes the win rate from the round trips after commissions', () => {
    const trades = [
      trade('BUY', '10', '100'),
      trade('SELL', '10', '110'),
      trade('BUY', '5', '100'),
      trade('SELL', '5', '99'),
      trade('BUY', '2', '50'),
      trade('SELL', '1', '60'),
      trade('SELL', '1', '60'),
    ];

    const tiles = readKeyMetrics({ metrics: METRICS, startCapitalUsd: '100000', trades });

    // Round trips: +98 (won), -7 (lost), +17 (won).
    expect(tiles[3]?.text).toBe('66.7 %');
  });

  it('counts a round trip that only covers its commissions as lost', () => {
    const trades = [trade('BUY', '1', '100', '1'), trade('SELL', '1', '102', '1')];

    const tiles = readKeyMetrics({ metrics: METRICS, startCapitalUsd: '100000', trades });

    expect(tiles[3]?.text).toBe('0.0 %');
  });
});
