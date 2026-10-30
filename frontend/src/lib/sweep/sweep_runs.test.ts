// Sorts the "Runs" table of a sweep by 1 column (backtest.md section 10.11.4).
import { describe, expect, it } from 'vite-plus/test';
import { sortSweepRows, type SweepRow } from './sweep_runs';

const rows: SweepRow[] = [
  { backtestId: 1, values: { roc_period: 5, total_return: 0.1 } },
  { backtestId: 2, values: { roc_period: 10, total_return: null } },
  { backtestId: 3, values: { roc_period: 15, total_return: 0.3 } },
];

describe('sortSweepRows', () => {
  it('sorts from high to low and puts a row without a value last', () => {
    const sorted = sortSweepRows(rows, 'total_return', 'descending');
    expect(sorted.map((row) => row.backtestId)).toEqual([3, 1, 2]);
  });

  it('sorts from low to high and puts a row without a value last', () => {
    const sorted = sortSweepRows(rows, 'total_return', 'ascending');
    expect(sorted.map((row) => row.backtestId)).toEqual([1, 3, 2]);
  });

  it('does not change the given rows', () => {
    sortSweepRows(rows, 'roc_period', 'descending');
    expect(rows.map((row) => row.backtestId)).toEqual([1, 2, 3]);
  });
});
