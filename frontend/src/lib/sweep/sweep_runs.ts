// The rows of the "Runs" table of a sweep (backtest.md section 10.11.4): 1 row for each run, with the parameter
// values and the key metrics. Each column can sort the rows.

export type SortDirection = 'ascending' | 'descending';

export interface SweepRow {
  backtestId: number;
  values: Record<string, number | boolean | null>;
}

// A row without a value in the column goes last in both directions.
export function sortSweepRows(rows: SweepRow[], column: string, direction: SortDirection): SweepRow[] {
  const sign = direction === 'ascending' ? 1 : -1;
  return [...rows].sort((left, right) => {
    const leftValue = left.values[column] ?? null;
    const rightValue = right.values[column] ?? null;
    if (leftValue === null || rightValue === null) {
      return (leftValue === null ? 1 : 0) - (rightValue === null ? 1 : 0);
    }
    return sign * (Number(leftValue) - Number(rightValue));
  });
}
