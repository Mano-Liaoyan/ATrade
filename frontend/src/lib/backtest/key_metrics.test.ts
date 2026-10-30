// The key metric row of a test: one set of metrics in one order with one sign rule on all pages (spec #99, #137).
import { describe, expect, it } from 'vite-plus/test';
import { readKeyMetrics } from './index';

const METRICS = {
  final_equity_usd: '112345.6',
  total_return_percent: '12.3456',
  max_drawdown_percent: '37.71',
  trade_count: 4,
  sharpe_ratio: '1.23',
  win_rate_percent: '66.67',
};

describe('readKeyMetrics', () => {
  it('gives the 7 metrics in one order with names and signed texts', () => {
    const tiles = readKeyMetrics({ metrics: METRICS, startCapitalUsd: '100000' });

    expect(tiles.map((tile) => [tile.name, tile.text])).toEqual([
      ['Total return', '+12.35 %'],
      ['Net profit (USD)', '+12,345.60'],
      ['Max drawdown', '-37.71 %'],
      ['Sharpe ratio', '1.23'],
      ['Win rate', '66.67 %'],
      ['Trades', '4'],
      ['Final equity (USD)', '112,345.60'],
    ]);
  });

  it('gives the direction of the return, the profit, and the drawdown', () => {
    const tiles = readKeyMetrics({
      metrics: { ...METRICS, final_equity_usd: '90000', total_return_percent: '-10' },
      startCapitalUsd: '100000',
    });

    expect(tiles.map((tile) => tile.change)).toEqual([-10, -10000, -37.71, undefined, undefined, undefined, undefined]);
  });

  it('shows a max drawdown of 0 without a sign', () => {
    const tiles = readKeyMetrics({ metrics: { ...METRICS, max_drawdown_percent: '0' }, startCapitalUsd: '1' });

    expect(tiles[2]).toEqual({ name: 'Max drawdown', text: '0.00 %', change: 0 });
  });

  it('shows a dash for the net profit when the start capital is not known', () => {
    const tiles = readKeyMetrics({ metrics: METRICS, startCapitalUsd: null });

    expect(tiles[1]).toEqual({ name: 'Net profit (USD)', text: '–', change: null });
  });

  it('shows a dash for a Sharpe ratio and a win rate that the API gives as null', () => {
    const tiles = readKeyMetrics({
      metrics: { ...METRICS, sharpe_ratio: null, win_rate_percent: null },
      startCapitalUsd: '100000',
    });

    expect([tiles[3]?.text, tiles[4]?.text]).toEqual(['–', '–']);
  });

  it('gives the same names with dashes for a test without a result', () => {
    const tiles = readKeyMetrics({ metrics: null, startCapitalUsd: '100000' });

    expect(tiles).toEqual([
      { name: 'Total return', text: '–' },
      { name: 'Net profit (USD)', text: '–' },
      { name: 'Max drawdown', text: '–' },
      { name: 'Sharpe ratio', text: '–' },
      { name: 'Win rate', text: '–' },
      { name: 'Trades', text: '–' },
      { name: 'Final equity (USD)', text: '–' },
    ]);
  });
});
