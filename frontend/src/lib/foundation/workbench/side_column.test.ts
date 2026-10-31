// The width of a side column: its range, the splitter keys and drag, and the stored layout.
import { describe, expect, it } from 'vite-plus/test';
import {
  findSideColumnGrowDirection,
  findSideColumnRange,
  findSideColumnWidth,
  findSplitterDragValue,
  findSplitterKeyValue,
  readSideColumnLayout,
  toPixels,
  type SideColumnSide,
  type SplitterDrag,
  type SplitterRange,
} from './index';

const REM = 16;

function findKeyWidth(key: string, side: SideColumnSide, range: SplitterRange & { value: number }): number | null {
  return findSplitterKeyValue(key, { ...range, step: 16 }, findSideColumnGrowDirection(side));
}

function findDragWidth(drag: SplitterDrag, pointerX: number, side: SideColumnSide, range: SplitterRange): number {
  return findSplitterDragValue(drag, pointerX, range, findSideColumnGrowDirection(side));
}

describe('findSideColumnRange', () => {
  it('goes from 16rem to 60% of the workbench', () => {
    expect(findSideColumnRange({ workbenchPixels: 1600, otherColumnsPixels: 0, remPixels: REM })).toEqual({
      min: 256,
      max: 960,
    });
  });

  it('keeps 24rem for the center area', () => {
    // 1000 - 300 (the other column) - 384 (24rem) = 316, less than 60% (600).
    expect(findSideColumnRange({ workbenchPixels: 1000, otherColumnsPixels: 300, remPixels: REM })).toEqual({
      min: 256,
      max: 316,
    });
  });

  it('never gives a maximum below the minimum', () => {
    expect(findSideColumnRange({ workbenchPixels: 500, otherColumnsPixels: 0, remPixels: REM })).toEqual({
      min: 256,
      max: 256,
    });
  });
});

describe('the splitter keys of a side column', () => {
  const range = { min: 256, max: 960 };

  it('moves the splitter 16px with Arrow Left and Arrow Right', () => {
    expect(findKeyWidth('ArrowRight', 'start', { value: 400, ...range })).toBe(416);
    expect(findKeyWidth('ArrowLeft', 'start', { value: 400, ...range })).toBe(384);
    // The splitter of a right column is on its left edge: Arrow Left makes the column wider.
    expect(findKeyWidth('ArrowLeft', 'end', { value: 400, ...range })).toBe(416);
    expect(findKeyWidth('ArrowRight', 'end', { value: 400, ...range })).toBe(384);
  });

  it('gives the minimum width with Home and the maximum width with End', () => {
    expect(findKeyWidth('Home', 'start', { value: 400, ...range })).toBe(256);
    expect(findKeyWidth('End', 'end', { value: 400, ...range })).toBe(960);
  });

  it('stays in the range and ignores other keys', () => {
    expect(findKeyWidth('ArrowLeft', 'start', { value: 260, ...range })).toBe(256);
    expect(findKeyWidth('ArrowUp', 'start', { value: 400, ...range })).toBeNull();
  });
});

describe('a pointer drag on the splitter of a side column', () => {
  const drag = { startPointerPixels: 500, startValue: 400 };
  const range = { min: 256, max: 960 };

  it('follows the pointer: a left column gets wider to the right, a right column to the left', () => {
    expect(findDragWidth(drag, 550, 'start', range)).toBe(450);
    expect(findDragWidth(drag, 550, 'end', range)).toBe(350);
  });

  it('stays in the range', () => {
    expect(findDragWidth(drag, 2000, 'start', range)).toBe(960);
    expect(findDragWidth(drag, 2000, 'end', range)).toBe(256);
  });
});

describe('toPixels', () => {
  it('reads rem and px widths', () => {
    expect(toPixels('17.5rem', REM)).toBe(280);
    expect(toPixels('300px', REM)).toBe(300);
  });
});

describe('readSideColumnLayout', () => {
  it('reads the width and the minimized state', () => {
    expect(readSideColumnLayout({ isMinimized: true, widthPixels: 420 })).toEqual({
      isMinimized: true,
      widthPixels: 420,
    });
  });

  it('reads an old collapsed column as minimized with the default width', () => {
    expect(readSideColumnLayout({ isCollapsed: true })).toEqual({ isMinimized: true, widthPixels: null });
  });

  it('gives an open column with the default width for a missing or damaged value', () => {
    expect(readSideColumnLayout(null)).toEqual({ isMinimized: false, widthPixels: null });
    expect(readSideColumnLayout({ isMinimized: 'yes', widthPixels: 'wide' })).toEqual({
      isMinimized: false,
      widthPixels: null,
    });
  });
});

describe('findSideColumnWidth', () => {
  const range = { min: 256, max: 576 };

  it('gives the width that the user set, or the default width, in the range', () => {
    expect(findSideColumnWidth(400, '20rem', range, REM)).toBe(400);
    expect(findSideColumnWidth(null, '20rem', range, REM)).toBe(320);
    expect(findSideColumnWidth(null, '36rem', range, REM)).toBe(576);
    expect(findSideColumnWidth(100, '20rem', range, REM)).toBe(256);
  });
});
