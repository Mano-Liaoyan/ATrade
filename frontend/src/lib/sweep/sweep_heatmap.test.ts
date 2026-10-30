// Turns the runs of a 2-parameter sweep into heatmap rows and columns of 1 metric.
import { describe, expect, it } from 'vite-plus/test';
import { readHeatmap } from './sweep_heatmap';

const runs = [
  { parameters: { a: 1, b: 10 }, value: 0.5 },
  { parameters: { a: 2, b: 10 }, value: 0.25 },
  { parameters: { a: 1, b: 20 }, value: null },
];

describe('readHeatmap', () => {
  it('puts the first parameter on the columns and the second on the rows', () => {
    const heatmap = readHeatmap(runs, 'a', 'b');

    expect(heatmap.columns).toEqual([1, 2]);
    expect(heatmap.rows).toEqual([10, 20]);
    expect(heatmap.cells).toEqual([
      [0.5, 0.25],
      [null, null],
    ]);
  });

  it('scales a value from 0 (lowest) to 1 (highest) for the sequential color', () => {
    const heatmap = readHeatmap(runs, 'a', 'b');

    expect(heatmap.shade(0.25)).toBe(0);
    expect(heatmap.shade(0.5)).toBe(1);
  });
});
