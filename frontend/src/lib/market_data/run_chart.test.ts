// The link of a backtest or forward test bar chart with its Trades or Fills table (indicator.md section 23.9.9).
import { describe, expect, it } from 'vite-plus/test';
import type { ChartIndicatorSet } from './chart_indicator_set';
import { findRowTrade, findRingTrades, RunChart } from './run_chart.svelte';

// Row 1 is a split adjustment: it has no trade mark.
const TRADE_INDEX_BY_ROW = [0, null, 1, 2];

describe('findRingTrades', () => {
  it('gives the trades of the pointed row and of the selected row', () => {
    expect(findRingTrades(TRADE_INDEX_BY_ROW, 0, 3)).toEqual([0, 2]);
  });

  it('leaves out a row without a trade and a missing row', () => {
    expect(findRingTrades(TRADE_INDEX_BY_ROW, 1, null)).toEqual([]);
    expect(findRingTrades(TRADE_INDEX_BY_ROW, null, 9)).toEqual([]);
  });
});

describe('findRowTrade', () => {
  it('gives the trade of a row, or null', () => {
    expect(findRowTrade(TRADE_INDEX_BY_ROW, 2)).toBe(1);
    expect(findRowTrade(TRADE_INDEX_BY_ROW, 1)).toBeNull();
    expect(findRowTrade(TRADE_INDEX_BY_ROW, null)).toBeNull();
  });
});

describe('RunChart.findInstrument', () => {
  const instruments = [
    { symbol: 'AAPL', exchange: 'NASDAQ' },
    { symbol: 'MSFT', exchange: 'NASDAQ' },
  ];

  it('gives the first instrument without a selection', () => {
    expect(new RunChart().findInstrument('1', instruments)).toEqual(instruments[0]);
    expect(new RunChart().findInstrument('1', instruments.slice(2))).toBeUndefined();
  });

  it('gives the selected instrument of the run only', () => {
    const chart = new RunChart();
    chart.selectInstrument('1', { symbol: 'MSFT', exchange: 'NASDAQ' });

    expect(chart.findInstrument('1', instruments)).toEqual(instruments[1]);
    expect(chart.findInstrument('2', instruments)).toEqual(instruments[0]);
  });
});

describe('RunChart.indicators', () => {
  const SMA = { indicator: 'sma', parameters: { period: 50 }, hidden: false, lines: [{ output: 'value', color: 1, style: 'solid' as const, width: 2 }] };
  const STRATEGY_SMA = { ...SMA, parameters: { period: 20 }, isFromStrategy: true as const };

  it('saves a change of a run chart in the chart indicator set without the strategy indicators', async () => {
    const savedSets: ChartIndicatorSet[] = [];
    const fetchFunction: typeof fetch = (_input, init) => {
      if (init?.method === 'PUT') {
        savedSets.push(JSON.parse(init.body as string) as ChartIndicatorSet);
      }
      return Promise.resolve(new Response(JSON.stringify({ panes: [{ indicators: [] }], favorites: ['rsi'] })));
    };
    const chart = new RunChart();
    await chart.indicatorSet.load(fetchFunction);

    chart.indicators.changePanes(fetchFunction, '1', [{ indicators: [STRATEGY_SMA, SMA] }]);

    expect(chart.indicators.readPanes('1', [])).toEqual([{ indicators: [STRATEGY_SMA, SMA] }]);
    // Another run shows the saved panes.
    expect(chart.indicators.readPanes('2', [])).toEqual([{ indicators: [SMA] }]);
    await expect.poll(() => savedSets).toEqual([{ panes: [{ indicators: [SMA] }], favorites: ['rsi'] }]);
  });

  it('does not save a change before the saved set is read: the saved set stays', async () => {
    let putCount = 0;
    const fetchFunction: typeof fetch = (_input, init) => {
      putCount += init?.method === 'PUT' ? 1 : 0;
      return Promise.resolve(new Response(JSON.stringify({ panes: [{ indicators: [SMA] }], favorites: [] })));
    };
    const chart = new RunChart();

    chart.indicators.changePanes(fetchFunction, '1', [{ indicators: [STRATEGY_SMA] }]);
    await chart.indicatorSet.load(fetchFunction);

    expect(chart.indicators.readPanes('1', [])).toEqual([{ indicators: [STRATEGY_SMA] }]);
    expect(chart.indicators.readPanes('2', [])).toEqual([{ indicators: [SMA] }]);
    expect(putCount).toBe(0);
  });
});
