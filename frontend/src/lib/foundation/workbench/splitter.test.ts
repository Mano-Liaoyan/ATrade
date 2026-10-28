// The splitter moves with the arrow keys, Home, and End, and with a pointer drag.
import { describe, expect, it } from 'vite-plus/test';
import { findSplitterDragValue, findSplitterKeyValue } from './index';

describe('findSplitterKeyValue', () => {
  const range = { value: 240, min: 96, max: 640, step: 16 };

  it('makes the second panel taller with Arrow Up and smaller with Arrow Down', () => {
    expect(findSplitterKeyValue('ArrowUp', range)).toBe(256);
    expect(findSplitterKeyValue('ArrowDown', range)).toBe(224);
  });

  it('gives the controlled panel its minimum with Home and its maximum with End (WAI-ARIA window splitter)', () => {
    expect(findSplitterKeyValue('Home', range)).toBe(96);
    expect(findSplitterKeyValue('End', range)).toBe(640);
  });

  it('stays in the range', () => {
    expect(findSplitterKeyValue('ArrowDown', { ...range, value: 100 })).toBe(96);
  });

  it('ignores other keys', () => {
    expect(findSplitterKeyValue('Enter', range)).toBeNull();
  });
});

describe('findSplitterDragValue', () => {
  it('makes the second panel taller when the pointer moves up', () => {
    const drag = { startPointerPixels: 500, startValue: 240 };

    expect(findSplitterDragValue(drag, 450, { min: 96, max: 640 })).toBe(290);
    expect(findSplitterDragValue(drag, 900, { min: 96, max: 640 })).toBe(96);
  });
});
