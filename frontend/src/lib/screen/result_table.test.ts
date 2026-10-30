// The columns, the sort, and the exclusion reasons of the screen result tables (screen.md section 24.10.2).
import { describe, expect, it } from 'vite-plus/test';
import { describeExclusionReason, listResultColumns, sortResultRows, type ScreenResultRow } from './result_table';

function row(position: number, symbol: string, close: string, rsi: number, percentile: number): ScreenResultRow {
  return {
    position,
    symbol,
    exchange: 'NASDAQ',
    currency: 'USD',
    last_price: close,
    average_trading_value_20: position === 2 ? null : 1000 * position,
    indicator_values: { 'RSI(14)': rsi, 'SMA(3)': rsi },
    percentiles: { 'RSI(14)': percentile },
  };
}

describe('listResultColumns', () => {
  it('adds one column for each indicator and one Percentile column for each rank condition', () => {
    const columns = listResultColumns(
      { indicator_conditions: [{ kind: 'compare' }, { kind: 'rank' }] },
      { indicator_conditions: ['RSI(14)', 'SMA(3)'], order: 'RSI(14)' },
    );

    expect(columns.map((column) => [column.header, column.isNumber])).toEqual([
      ['#', true],
      ['Symbol', false],
      ['Exchange', false],
      ['Close', true],
      ['Avg trading value (20)', true],
      ['RSI(14)', true],
      ['SMA(3)', true],
      ['Percentile', true],
    ]);
  });

  it('names each Percentile column by its indicator when there are 2 rank conditions', () => {
    const columns = listResultColumns(
      { indicator_conditions: [{ kind: 'rank' }, { kind: 'rank' }] },
      { indicator_conditions: ['RSI(14)', 'SMA(3)'], order: 'RSI(14)' },
    );

    expect(columns.slice(-2).map((column) => column.header)).toEqual(['Percentile RSI(14)', 'Percentile SMA(3)']);
  });
});

describe('sortResultRows', () => {
  const rows = [row(1, 'AAPL', '30', 20, 100), row(2, 'MSFT', '120.5', 40, 50), row(3, 'TSLA', '9', 10, 25)];
  const columns = listResultColumns(
    { indicator_conditions: [{ kind: 'rank' }] },
    { indicator_conditions: ['RSI(14)'], order: 'SMA(3)' },
  );

  function sortedSymbols(header: string, direction: 'ascending' | 'descending'): string[] {
    const column = columns.find((candidate) => candidate.header === header);
    if (column === undefined) {
      throw new Error(header);
    }
    return sortResultRows(rows, column, direction).map((item) => item.symbol);
  }

  it('sorts number columns by number and text columns by text', () => {
    expect(sortedSymbols('Close', 'ascending')).toEqual(['TSLA', 'AAPL', 'MSFT']);
    expect(sortedSymbols('RSI(14)', 'descending')).toEqual(['MSFT', 'AAPL', 'TSLA']);
    expect(sortedSymbols('Symbol', 'descending')).toEqual(['TSLA', 'MSFT', 'AAPL']);
  });

  it('puts the rows without a value last in both directions', () => {
    expect(sortedSymbols('Avg trading value (20)', 'ascending')).toEqual(['AAPL', 'TSLA', 'MSFT']);
    expect(sortedSymbols('Avg trading value (20)', 'descending')).toEqual(['TSLA', 'AAPL', 'MSFT']);
  });
});

describe('describeExclusionReason', () => {
  it('shows the condition without its location', () => {
    expect(describeExclusionReason('filters[0]: Close > 15')).toBe('Close > 15');
    expect(describeExclusionReason('indicator_conditions[2]: RSI(14) < 30')).toBe('RSI(14) < 30');
    expect(describeExclusionReason('No value: RSI(14)')).toBe('No value: RSI(14)');
    expect(describeExclusionReason('No daily bars')).toBe('No daily bars');
  });
});
