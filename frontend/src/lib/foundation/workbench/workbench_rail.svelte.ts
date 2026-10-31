// The rail state of a workbench: while a side column is maximized, the center area of the workbench is a 32px rail
// and its content stays in the page (docs/architecture/assistant.md 25.12.3). Workbench gives the state to its side
// columns as a Svelte context.
import { getContext, setContext } from 'svelte';

const WORKBENCH_RAIL_KEY = Symbol('workbench-rail');

export class WorkbenchRail {
  isRail = $state(false);
}

export function provideWorkbenchRail(): WorkbenchRail {
  return setContext(WORKBENCH_RAIL_KEY, new WorkbenchRail());
}

/** Undefined for a side column outside a Workbench. */
export function readWorkbenchRail(): WorkbenchRail | undefined {
  return getContext<WorkbenchRail | undefined>(WORKBENCH_RAIL_KEY);
}
