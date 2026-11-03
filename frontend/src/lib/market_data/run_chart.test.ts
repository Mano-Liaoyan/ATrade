// The link of a backtest or forward test bar chart with its Trades or Fills table (indicator.md section 23.9.9).
import { describe, expect, it } from 'vite-plus/test';
import { findRowTrade, findRingTrades } from './run_chart.svelte';

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
