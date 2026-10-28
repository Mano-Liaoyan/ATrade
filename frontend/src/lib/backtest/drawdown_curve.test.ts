// The drawdown curve under the equity curve: the same sign rule as the max drawdown metric (negative percent).
import { describe, expect, it } from 'vite-plus/test';
import { computeDrawdownCurve } from './index';

function point(timeUtc: string, equityUsd: string): { time_utc: string; equity_usd: string } {
  return { time_utc: timeUtc, equity_usd: equityUsd };
}

describe('computeDrawdownCurve', () => {
  it('gives the fall from the highest equity so far as a negative percent', () => {
    const curve = computeDrawdownCurve(
      [point('2024-01-01T00:00:00Z', '100'), point('2024-01-02T00:00:00Z', '120'), point('2024-01-03T00:00:00Z', '90')],
      '100',
    );

    expect(curve).toEqual([
      { timeUtc: '2024-01-01T00:00:00Z', drawdownPercent: 0 },
      { timeUtc: '2024-01-02T00:00:00Z', drawdownPercent: 0 },
      { timeUtc: '2024-01-03T00:00:00Z', drawdownPercent: -25 },
    ]);
  });

  it('starts the highest equity at the start capital, like the max drawdown metric', () => {
    const curve = computeDrawdownCurve([point('2024-01-01T00:00:00Z', '80')], '100');

    expect(curve).toEqual([{ timeUtc: '2024-01-01T00:00:00Z', drawdownPercent: -20 }]);
  });

  it('starts at the first equity point when the start capital is not known', () => {
    const curve = computeDrawdownCurve([point('2024-01-01T00:00:00Z', '80'), point('2024-01-02T00:00:00Z', '60')], null);

    expect(curve).toEqual([
      { timeUtc: '2024-01-01T00:00:00Z', drawdownPercent: 0 },
      { timeUtc: '2024-01-02T00:00:00Z', drawdownPercent: -25 },
    ]);
  });
});
