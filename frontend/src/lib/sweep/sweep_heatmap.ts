// The heatmap of a sweep of 2 or 3 parameters (backtest.md section 10.11.4): the first parameter on the columns,
// the second on the rows, and 1 metric value in each cell.
export type ParameterValue = number | boolean;

export interface HeatmapRun {
  parameters: Record<string, ParameterValue>;
  value: number | null;
}

export interface Heatmap {
  columns: ParameterValue[];
  rows: ParameterValue[];
  cells: (number | null)[][];
  /** The Carbon sequential color step of a value: 1 for the lowest metric value, 10 for the highest. */
  step: (value: number) => number;
}

export const SEQUENTIAL_STEP_COUNT = 10;

/** The values of 1 parameter in the runs, from low to high (false before true). */
export function listParameterValues(runs: HeatmapRun[], name: string): ParameterValue[] {
  const values = new Set(runs.flatMap((run) => (name in run.parameters ? [run.parameters[name] as ParameterValue] : [])));
  return [...values].sort((left, right) => Number(left) - Number(right));
}

function cellKey(column: ParameterValue, row: ParameterValue): string {
  return `${String(column)}|${String(row)}`;
}

export function readHeatmap(runs: HeatmapRun[], columnParameter: string, rowParameter: string): Heatmap {
  const columns = listParameterValues(runs, columnParameter);
  const rows = listParameterValues(runs, rowParameter);
  const valueByCell = new Map(
    runs.map((run) => [cellKey(run.parameters[columnParameter] ?? 0, run.parameters[rowParameter] ?? 0), run.value]),
  );
  const cells = rows.map((row) => columns.map((column) => valueByCell.get(cellKey(column, row)) ?? null));
  const values = runs.flatMap((run) => (run.value === null ? [] : [run.value]));
  const lowest = Math.min(...values);
  const highest = Math.max(...values);
  const step = (value: number) =>
    highest === lowest
      ? SEQUENTIAL_STEP_COUNT
      : 1 + Math.round(((value - lowest) / (highest - lowest)) * (SEQUENTIAL_STEP_COUNT - 1));
  return { columns, rows, cells, step };
}
