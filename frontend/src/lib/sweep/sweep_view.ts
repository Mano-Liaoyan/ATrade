// What the sweep page shows of 1 sweep (backtest.md section 10.11.4): the chart of the selected metric (points for 1
// parameter, a heatmap for 2 or 3) and the rows of the "Runs" table.
import { formatSignedPercent, MISSING_VALUE } from '#lib/foundation/value_format';
import type { SweepDetail, SweepRun } from './sweep_api';
import { listParameterValues, readHeatmap, type Heatmap, type HeatmapRun, type ParameterValue } from './sweep_heatmap';
import type { SweepRow } from './sweep_runs';

export type SweepMetricKey =
  | 'total_return_percent'
  | 'max_drawdown_percent'
  | 'sharpe_ratio'
  | 'win_rate_percent'
  | 'trade_count';

/** The metrics of the "Metric" select and the Runs table, in the order of the key metric row. */
export const SWEEP_METRICS: readonly { value: SweepMetricKey; label: string }[] = [
  { value: 'total_return_percent', label: 'Total return' },
  { value: 'max_drawdown_percent', label: 'Max drawdown' },
  { value: 'sharpe_ratio', label: 'Sharpe ratio' },
  { value: 'win_rate_percent', label: 'Win rate' },
  { value: 'trade_count', label: 'Trades' },
];

export const DEFAULT_SWEEP_METRIC: SweepMetricKey = 'total_return_percent';

export interface SweepPoint {
  parameterValue: ParameterValue;
  value: number | null;
}

export interface SweepSlice {
  parameter: string;
  values: ParameterValue[];
  value: ParameterValue;
}

export type SweepChart =
  | { kind: 'points'; parameter: string; points: SweepPoint[] }
  | { kind: 'heatmap'; columnParameter: string; rowParameter: string; heatmap: Heatmap; slice: SweepSlice | null };

const RATIO_FORMAT = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** The value of 1 metric of a run. The max drawdown is a loss, so it is negative, like the key metric row. */
export function readSweepMetric(run: SweepRun, key: SweepMetricKey): number | null {
  const metric = run.metrics?.[key] ?? null;
  if (metric === null) {
    return null;
  }
  const value = Number(metric);
  return key === 'max_drawdown_percent' && value !== 0 ? -value : value;
}

export function formatSweepMetric(key: SweepMetricKey, value: number | null): string {
  if (value === null) {
    return MISSING_VALUE;
  }
  if (key === 'total_return_percent' || key === 'max_drawdown_percent') {
    return formatSignedPercent(value);
  }
  if (key === 'win_rate_percent') {
    return `${RATIO_FORMAT.format(value)} %`;
  }
  return key === 'trade_count' ? String(value) : RATIO_FORMAT.format(value);
}

// A sweep has no status column (section 10.11.2). Its status is the first status of this order that has runs, but
// "finished" comes before the other final statuses.
const SWEEP_STATUS_ORDER: readonly SweepRun['status'][] = ['running', 'queued', 'finished', 'failed', 'timed_out', 'cancelled'];

/** The status of a sweep from the run count of each status. */
export function readSweepStatus(statusCounts: Record<string, number>): SweepRun['status'] {
  return SWEEP_STATUS_ORDER.find((status) => (statusCounts[status] ?? 0) > 0) ?? 'queued';
}

export function readParameterNames(sweep: SweepDetail): string[] {
  return sweep.grid.map((entry) => String(entry.name));
}

export function readSweepChart(sweep: SweepDetail, metric: SweepMetricKey, sliceValue: ParameterValue | null): SweepChart {
  const [columnParameter = '', rowParameter, sliceParameter] = readParameterNames(sweep);
  const runs: HeatmapRun[] = sweep.runs.map((run) => ({
    parameters: run.parameters,
    value: readSweepMetric(run, metric),
  }));
  if (rowParameter === undefined) {
    const points = runs.map((run) => ({ parameterValue: run.parameters[columnParameter] ?? 0, value: run.value }));
    points.sort((left, right) => Number(left.parameterValue) - Number(right.parameterValue));
    return { kind: 'points', parameter: columnParameter, points };
  }
  if (sliceParameter === undefined) {
    return { kind: 'heatmap', columnParameter, rowParameter, heatmap: readHeatmap(runs, columnParameter, rowParameter), slice: null };
  }
  const values = listParameterValues(runs, sliceParameter);
  const value = sliceValue !== null && values.includes(sliceValue) ? sliceValue : (values[0] ?? 0);
  const sliceRuns = runs.filter((run) => run.parameters[sliceParameter] === value);
  return {
    kind: 'heatmap',
    columnParameter,
    rowParameter,
    heatmap: readHeatmap(sliceRuns, columnParameter, rowParameter),
    slice: { parameter: sliceParameter, values, value },
  };
}

export function readSweepRows(sweep: SweepDetail): SweepRow[] {
  return sweep.runs.map((run) => ({
    backtestId: run.backtest_id,
    status: run.status,
    values: {
      ...run.parameters,
      ...Object.fromEntries(SWEEP_METRICS.map(({ value: key }) => [key, readSweepMetric(run, key)])),
    },
  }));
}
