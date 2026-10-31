// The width of a side column (SideColumn.svelte). The splitter on its inner edge changes the width: a pointer drag,
// Arrow Left and Arrow Right 16px, Home the minimum, End the maximum. The width is 16rem to 60% of the workbench, and
// the center area keeps at least 24rem. The browser keeps the width and the minimized state under `storageKey`.
import type { SplitterRange } from './splitter';

export type SideColumnSide = 'start' | 'end';

const MIN_REM = 16;
const CENTER_MIN_REM = 24;
const MAX_SHARE = 0.6;
export const DEFAULT_REM_PIXELS = 16;

export interface SideColumnRangeInput {
  workbenchPixels: number;
  /** The width of the other side columns of the workbench. */
  otherColumnsPixels: number;
  remPixels: number;
}

export function findSideColumnRange(input: SideColumnRangeInput): SplitterRange {
  const min = MIN_REM * input.remPixels;
  const centerMax = input.workbenchPixels - input.otherColumnsPixels - CENTER_MIN_REM * input.remPixels;
  const max = Math.min(MAX_SHARE * input.workbenchPixels, centerMax);
  return { min, max: Math.max(min, max) };
}

/**
 * The direction in which the splitter moves to make the column wider. The splitter of a left column is on its right
 * edge, so the column gets wider when the splitter moves right.
 */
export function findSideColumnGrowDirection(side: SideColumnSide): 'left' | 'right' {
  return side === 'start' ? 'right' : 'left';
}

/** The pixels of a CSS width in rem or px, for example the default width "17.5rem". */
export function toPixels(width: string, remPixels: number): number {
  const amount = Number.parseFloat(width);
  return width.trim().endsWith('rem') ? amount * remPixels : amount;
}

/** The pixels of 1rem in the page. The browser default when the root font size is not a number. */
export function readRemPixels(): number {
  const pixels = Number.parseFloat(getComputedStyle(document.documentElement).fontSize);
  return Number.isNaN(pixels) ? DEFAULT_REM_PIXELS : pixels;
}

/** The shown width: the width that the user set, or the default width, in the range. */
export function findSideColumnWidth(
  widthPixels: number | null,
  defaultWidth: string,
  range: SplitterRange,
  remPixels: number,
): number {
  return Math.min(Math.max(widthPixels ?? toPixels(defaultWidth, remPixels), range.min), range.max);
}

export interface SideColumnLayout {
  isMinimized: boolean;
  /** Null gives the default width. */
  widthPixels: number | null;
}

/**
 * The stored layout of a SideColumn. A missing or damaged value gives an open column with the default width. A value
 * stored before the splitter (`isCollapsed` only) gives the default width.
 */
export function readSideColumnLayout(stored: unknown): SideColumnLayout {
  if (typeof stored !== 'object' || stored === null) {
    return { isMinimized: false, widthPixels: null };
  }
  const isMinimized = Reflect.get(stored, 'isMinimized') === true || Reflect.get(stored, 'isCollapsed') === true;
  const width: unknown = Reflect.get(stored, 'widthPixels');
  const widthPixels = typeof width === 'number' && Number.isFinite(width) && width > 0 ? width : null;
  return { isMinimized, widthPixels };
}
