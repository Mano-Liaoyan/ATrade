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

  it('gives the lowest value Carbon sequential step 1 and the highest step 10', () => {
    const heatmap = readHeatmap([...runs, { parameters: { a: 2, b: 20 }, value: 0.375 }], 'a', 'b');

    expect(heatmap.step(0.25)).toBe(1);
    expect(heatmap.step(0.375)).toBe(6);
    expect(heatmap.step(0.5)).toBe(10);
  });

  it('keeps false and true as the 2 values of a bool parameter', () => {
    const heatmap = readHeatmap(
      [
        { parameters: { a: true, b: 1 }, value: 1 },
        { parameters: { a: false, b: 1 }, value: 2 },
      ],
      'a',
      'b',
    );

    expect(heatmap.columns).toEqual([false, true]);
    expect(heatmap.cells).toEqual([[2, 1]]);
  });
});
