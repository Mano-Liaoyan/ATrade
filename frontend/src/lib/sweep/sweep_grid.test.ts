// Counts the runs of a parameter grid and tells why a sweep cannot start (backtest.md section 10.11.1).
import { describe, expect, it } from 'vite-plus/test';
import { buildSweepGrid, countSweepRuns, readSweepStartBlock } from './sweep_grid';

describe('buildSweepGrid', () => {
  it('has 1 entry for each checked parameter, and a bool parameter has only its name', () => {
    const rows = [
      { name: 'period', type: 'int', isSwept: true, start: '5', end: '40', step: '5' },
      { name: 'size', type: 'float', isSwept: false, start: '1', end: '2', step: '1' },
      { name: 'fast', type: 'bool', isSwept: true, start: '', end: '', step: '' },
    ];

    expect(buildSweepGrid(rows)).toEqual([{ name: 'period', start: 5, end: 40, step: 5 }, { name: 'fast' }]);
  });

  it('counts an empty range field as a range without values', () => {
    const grid = buildSweepGrid([{ name: 'period', type: 'int', isSwept: true, start: '5', end: '', step: '5' }]);

    expect(countSweepRuns(grid)).toBe(0);
  });
});

describe('countSweepRuns', () => {
  it('multiplies the value counts of the swept parameters', () => {
    const grid = [
      { name: 'roc_period', start: 5, end: 40, step: 5 },
      { name: 'rebalance_days', start: 5, end: 60, step: 5 },
    ];
    expect(countSweepRuns(grid)).toBe(8 * 12);
  });

  it('counts a parameter without a range as 1 value', () => {
    expect(countSweepRuns([{ name: 'roc_period' }])).toBe(1);
  });

  it('returns 0 for a range that has no values', () => {
    expect(countSweepRuns([{ name: 'roc_period', start: 10, end: 5, step: 1 }])).toBe(0);
    expect(countSweepRuns([{ name: 'roc_period', start: 1, end: 5, step: 0 }])).toBe(0);
  });
});

describe('readSweepStartBlock', () => {
  it('allows a grid of 1 to 3 parameters and up to 200 runs', () => {
    expect(readSweepStartBlock([{ name: 'a', start: 1, end: 200, step: 1 }])).toBeUndefined();
  });

  it('blocks a grid of more than 200 runs', () => {
    expect(readSweepStartBlock([{ name: 'a', start: 1, end: 201, step: 1 }])).toBe(
      'The grid has 201 runs. The limit is 200.',
    );
  });

  it('blocks a grid of more than 3 parameters', () => {
    const grid = ['a', 'b', 'c', 'd'].map((name) => ({ name, start: 1, end: 2, step: 1 }));
    expect(readSweepStartBlock(grid)).toBe('The grid has 4 parameters. The limit is 3.');
  });

  it('blocks a grid with a range without values', () => {
    expect(readSweepStartBlock([{ name: 'a', start: 5, end: 1, step: 1 }])).toBe(
      'A range has no values. Give a start, an end after it, and a step above 0.',
    );
  });

  it('blocks a grid without parameters', () => {
    expect(readSweepStartBlock([])).toBe('Select 1 to 3 parameters to sweep.');
  });
});
