// The grid rules of a parameter sweep (backtest.md section 10.11.1): 1 to 3 parameters, 200 runs or fewer.

import type { components } from '#lib/api';

export type GridEntry = components['schemas']['GridEntry'];

export const MAX_SWEEP_RUNS = 200;
export const MAX_SWEEP_PARAMETERS = 3;
// The small offset keeps a decimal step such as 0.1 from losing the last value.
const STEP_TOLERANCE = 1e-9;

function valueCount(entry: GridEntry): number {
  if (entry.start == null || entry.end == null || entry.step == null) {
    return 1;
  }
  const start = Number(entry.start);
  const end = Number(entry.end);
  const step = Number(entry.step);
  if (![start, end, step].every(Number.isFinite) || !(step > 0) || end < start) {
    return 0;
  }
  return Math.floor((end - start) / step + STEP_TOLERANCE) + 1;
}

export function countSweepRuns(grid: GridEntry[]): number {
  return grid.length === 0 ? 0 : grid.reduce((runs, entry) => runs * valueCount(entry), 1);
}

// The reason that "Start parameter sweep" is disabled, or undefined when the grid can start.
export function readSweepStartBlock(grid: GridEntry[]): string | undefined {
  if (grid.length === 0) {
    return 'Select 1 to 3 parameters to sweep.';
  }
  if (grid.length > MAX_SWEEP_PARAMETERS) {
    return `The grid has ${String(grid.length)} parameters. The limit is ${String(MAX_SWEEP_PARAMETERS)}.`;
  }
  const runs = countSweepRuns(grid);
  if (runs === 0) {
    return 'A range has no values. Give a start, an end after it, and a step above 0.';
  }
  if (runs > MAX_SWEEP_RUNS) {
    return `The grid has ${String(runs)} runs. The limit is ${String(MAX_SWEEP_RUNS)}.`;
  }
  return undefined;
}

/** 1 parameter row of the "New parameter sweep" dialog: the input texts of a range and the sweep check box. */
export interface SweepParameterInput {
  name: string;
  type: string;
  isSwept: boolean;
  start: string;
  end: string;
  step: string;
}

// An empty or wrong text gives NaN, and a range with NaN has no values (countSweepRuns).
function readNumber(text: string): number {
  return text.trim() === '' ? Number.NaN : Number(text);
}

/** The grid of the checked parameters. A bool parameter has only its name: the sweep uses both values. */
export function buildSweepGrid(rows: SweepParameterInput[]): GridEntry[] {
  return rows
    .filter((row) => row.isSwept)
    .map((row) =>
      row.type === 'bool'
        ? { name: row.name }
        : { name: row.name, start: readNumber(row.start), end: readNumber(row.end), step: readNumber(row.step) },
    );
}
