// The chart and the Runs rows of the sweep page come from one sweep and the selected metric.
import { describe, expect, it } from 'vite-plus/test';
import type { SweepDetail, SweepRun } from './sweep_api';
import { formatSweepMetric, readSweepChart, readSweepRows, readSweepStatus } from './sweep_view';

function makeRun(backtestId: number, parameters: SweepRun['parameters'], totalReturn: string | null): SweepRun {
  return {
    backtest_id: backtestId,
    parameters,
    status: totalReturn === null ? 'queued' : 'finished',
    metrics:
      totalReturn === null
        ? null
        : {
            final_equity_usd: '11000',
            total_return_percent: totalReturn,
            max_drawdown_percent: '12.5',
            trade_count: 4,
            cagr_percent: null,
            annual_volatility_percent: null,
            sharpe_ratio: '1.25',
            sortino_ratio: null,
            calmar_ratio: null,
            profit_factor: null,
            average_win_usd: null,
            average_win_percent: null,
            average_loss_usd: null,
            exposure_percent: null,
            turnover_per_year: null,
            win_rate_percent: '50',
            missing_reasons: {},
          },
  };
}

function makeSweep(names: string[], runs: SweepRun[]): SweepDetail {
  return {
    id: 3,
    strategy_version_id: 1,
    strategy_id: 1,
    strategy_name: 'Rotation',
    version_number: 2,
    grid: names.map((name) => ({ name, start: 1, end: 2, step: 1 })),
    created_at_utc: '2026-10-30T00:00:00Z',
    run_count: runs.length,
    status_counts: {},
    runs,
  };
}

describe('readSweepChart', () => {
  it('shows a sweep of 1 parameter as points of the selected metric', () => {
    const sweep = makeSweep(['period'], [makeRun(1, { period: 5 }, '2'), makeRun(2, { period: 10 }, null)]);

    const chart = readSweepChart(sweep, 'total_return_percent', null);

    expect(chart).toEqual({
      kind: 'points',
      parameter: 'period',
      points: [
        { parameterValue: 5, value: 2 },
        { parameterValue: 10, value: null },
      ],
    });
  });

  it('shows a sweep of 2 parameters as a heatmap of the selected metric', () => {
    const sweep = makeSweep(
      ['period', 'days'],
      [makeRun(1, { period: 5, days: 1 }, '2'), makeRun(2, { period: 10, days: 1 }, '4')],
    );

    const chart = readSweepChart(sweep, 'max_drawdown_percent', null);

    expect(chart.kind === 'heatmap' && chart.heatmap.cells).toEqual([[-12.5, -12.5]]);
  });

  it('shows the heatmap of 1 value of the third parameter and lists its values', () => {
    const sweep = makeSweep(
      ['period', 'days', 'fast'],
      [
        makeRun(1, { period: 5, days: 1, fast: true }, '2'),
        makeRun(2, { period: 5, days: 1, fast: false }, '4'),
      ],
    );

    const chart = readSweepChart(sweep, 'total_return_percent', false);

    expect(chart.kind === 'heatmap' && chart.slice).toEqual({ parameter: 'fast', values: [false, true], value: false });
    expect(chart.kind === 'heatmap' && chart.heatmap.cells).toEqual([[4]]);
  });

  it('starts with the first value of the third parameter', () => {
    const sweep = makeSweep(
      ['period', 'days', 'size'],
      [makeRun(1, { period: 5, days: 1, size: 20 }, '2'), makeRun(2, { period: 5, days: 1, size: 10 }, '4')],
    );

    const chart = readSweepChart(sweep, 'total_return_percent', null);

    expect(chart.kind === 'heatmap' && chart.slice?.value).toBe(10);
  });
});

describe('readSweepRows', () => {
  it('has the parameter values, the metric values, and the status of each run', () => {
    const sweep = makeSweep(['period'], [makeRun(7, { period: 5 }, '2')]);

    expect(readSweepRows(sweep)).toEqual([
      {
        backtestId: 7,
        status: 'finished',
        values: {
          period: 5,
          total_return_percent: 2,
          max_drawdown_percent: -12.5,
          sharpe_ratio: 1.25,
          win_rate_percent: 50,
          trade_count: 4,
        },
      },
    ]);
  });
});

describe('readSweepStatus', () => {
  it('is running while a run runs, then queued while a run waits', () => {
    expect(readSweepStatus({ finished: 2, running: 1, queued: 3 })).toBe('running');
    expect(readSweepStatus({ finished: 2, queued: 3 })).toBe('queued');
  });

  it('is finished when a run finished and no run waits', () => {
    expect(readSweepStatus({ finished: 2, failed: 1, cancelled: 4 })).toBe('finished');
  });

  it('is the status of the runs when no run finished', () => {
    expect(readSweepStatus({ failed: 2, timed_out: 1 })).toBe('failed');
    expect(readSweepStatus({ cancelled: 3 })).toBe('cancelled');
  });
});

describe('formatSweepMetric', () => {
  it('writes each metric like the key metric row', () => {
    expect(formatSweepMetric('total_return_percent', 1.6)).toBe('+1.60 %');
    expect(formatSweepMetric('max_drawdown_percent', -12.5)).toBe('-12.50 %');
    expect(formatSweepMetric('sharpe_ratio', 1.234)).toBe('1.23');
    expect(formatSweepMetric('win_rate_percent', 50)).toBe('50.00 %');
    expect(formatSweepMetric('trade_count', 4)).toBe('4');
    expect(formatSweepMetric('sharpe_ratio', null)).toBe('–');
  });
});
