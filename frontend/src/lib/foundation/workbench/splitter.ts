// A splitter (Splitter.svelte). Its value is the size of the region that it controls (the primary pane of the
// WAI-ARIA window splitter pattern) in pixels. `grow` is the direction in which the splitter moves to make that region
// bigger: "up" for the splitter above a panel, "left" or "right" for the splitter of a side column. Home gives the
// region its minimum size and End its maximum size.

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

export type SplitterGrowDirection = 'up' | 'left' | 'right';

const GROW_KEY: Record<SplitterGrowDirection, string> = { up: 'ArrowUp', left: 'ArrowLeft', right: 'ArrowRight' };
const SHRINK_KEY: Record<SplitterGrowDirection, string> = { up: 'ArrowDown', left: 'ArrowRight', right: 'ArrowLeft' };

function clamp(value: number, range: SplitterRange): number {
  return Math.min(Math.max(value, range.min), range.max);
}

/** The new value for a key. Null for a key that does not move the splitter. */
export function findSplitterKeyValue(
  key: string,
  range: SplitterKeyRange,
  grow: SplitterGrowDirection = 'up',
): number | null {
  const valueByKey: Record<string, number> = {
    [GROW_KEY[grow]]: range.value + range.step,
    [SHRINK_KEY[grow]]: range.value - range.step,
    Home: range.min,
    End: range.max,
  };
  const value = valueByKey[key];
  return value === undefined ? null : clamp(value, range);
}

/** The new value while the pointer drags the splitter. `pointerPixels` is clientY for "up" and clientX otherwise. */
export function findSplitterDragValue(
  drag: SplitterDrag,
  pointerPixels: number,
  range: SplitterRange,
  grow: SplitterGrowDirection = 'up',
): number {
  const moved = pointerPixels - drag.startPointerPixels;
  return clamp(drag.startValue + (grow === 'right' ? moved : -moved), range);
}
