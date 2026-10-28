// The splitter above a panel (Splitter.svelte). Its value is the height of that panel (the primary pane of the
// WAI-ARIA window splitter pattern) in pixels, so Arrow Up and a pointer move up make the panel taller. Home gives the
// panel its minimum height and End its maximum height.

export interface SplitterRange {
  min: number;
  max: number;
}

export interface SplitterKeyRange extends SplitterRange {
  value: number;
  step: number;
}

export interface SplitterDrag {
  startPointerPixels: number;
  startValue: number;
}

function clamp(value: number, range: SplitterRange): number {
  return Math.min(Math.max(value, range.min), range.max);
}

/** The new value for a key. Null for a key that does not move the splitter. */
export function findSplitterKeyValue(key: string, range: SplitterKeyRange): number | null {
  const valueByKey: Record<string, number> = {
    ArrowUp: range.value + range.step,
    ArrowDown: range.value - range.step,
    Home: range.min,
    End: range.max,
  };
  const value = valueByKey[key];
  return value === undefined ? null : clamp(value, range);
}

/** The new value while the pointer drags the splitter. */
export function findSplitterDragValue(drag: SplitterDrag, pointerPixels: number, range: SplitterRange): number {
  return clamp(drag.startValue - (pointerPixels - drag.startPointerPixels), range);
}
