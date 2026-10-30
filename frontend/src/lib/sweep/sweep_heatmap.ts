// The heatmap of a 2-parameter sweep (backtest.md section 10.11.4): the first parameter on the columns,
// the second on the rows, and 1 metric value in each cell.

export interface HeatmapRun {
  parameters: Record<string, number | boolean>;
  value: number | null;
}

export interface Heatmap {
  columns: number[];
  rows: number[];
  cells: (number | null)[][];
  // A value from 0 (lowest metric value) to 1 (highest), for the Carbon sequential color step.
  shade: (value: number) => number;
}

function sortedValues(runs: HeatmapRun[], name: string): number[] {
  const values = new Set(runs.map((run) => Number(run.parameters[name])));
  return [...values].sort((left, right) => left - right);
}

export function readHeatmap(runs: HeatmapRun[], columnParameter: string, rowParameter: string): Heatmap {
  const columns = sortedValues(runs, columnParameter);
  const rows = sortedValues(runs, rowParameter);
  const valueByCell = new Map(
    runs.map((run) => [`${String(run.parameters[columnParameter])}|${String(run.parameters[rowParameter])}`, run.value]),
  );
  const cells = rows.map((row) =>
    columns.map((column) => valueByCell.get(`${String(column)}|${String(row)}`) ?? null),
  );
  const values = runs.flatMap((run) => (run.value === null ? [] : [run.value]));
  const lowest = Math.min(...values);
  const highest = Math.max(...values);
  const shade = (value: number) => (highest === lowest ? 1 : (value - lowest) / (highest - lowest));
  return { columns, rows, cells, shade };
}
