// The state of two stacked workbench panels: minimize, maximize, restore, the splitter size, and the stored layout.
import { describe, expect, it } from 'vite-plus/test';
import {
  clampSecondPanelPixels,
  findPanelSize,
  formatPanelRows,
  isPanelHeaderOnly,
  readPanelSplitLayout,
  restorePanelSplit,
  togglePanelSize,
} from './index';

describe('togglePanelSize', () => {
  it('minimizes a panel and restores it with a second click', () => {
    const minimized = togglePanelSize('split', 'second', 'minimized');

    expect(minimized).toBe('second-minimized');
    expect(togglePanelSize(minimized, 'second', 'minimized')).toBe('split');
  });

  it('maximizes the other panel at once when one panel is minimized', () => {
    expect(togglePanelSize('second-minimized', 'first', 'maximized')).toBe('first-maximized');
  });
});

describe('findPanelSize and isPanelHeaderOnly', () => {
  it('shows only the header line of a minimized panel', () => {
    expect(findPanelSize('first-minimized', 'first')).toBe('minimized');
    expect(isPanelHeaderOnly('first-minimized', 'first')).toBe(true);
    expect(isPanelHeaderOnly('first-minimized', 'second')).toBe(false);
  });

  it('shows only the header line of the other panel when a panel is maximized', () => {
    expect(findPanelSize('second-maximized', 'second')).toBe('maximized');
    expect(findPanelSize('second-maximized', 'first')).toBe('normal');
    expect(isPanelHeaderOnly('second-maximized', 'first')).toBe(true);
    expect(isPanelHeaderOnly('second-maximized', 'second')).toBe(false);
  });
});

describe('restorePanelSplit', () => {
  it('restores a maximized panel and keeps a minimized panel', () => {
    expect(restorePanelSplit('first-maximized')).toBe('split');
    expect(restorePanelSplit('first-minimized')).toBe('first-minimized');
  });
});

describe('formatPanelRows', () => {
  it('gives the second panel its height in the split, with a row for the splitter', () => {
    expect(formatPanelRows('split', 240)).toBe('minmax(0, 1fr) auto 240px');
  });

  it('gives all the height to the panel that is not header only', () => {
    expect(formatPanelRows('first-maximized', 240)).toBe('minmax(0, 1fr) auto');
    expect(formatPanelRows('second-minimized', 240)).toBe('minmax(0, 1fr) auto');
    expect(formatPanelRows('first-minimized', 240)).toBe('auto minmax(0, 1fr)');
    expect(formatPanelRows('second-maximized', 240)).toBe('auto minmax(0, 1fr)');
  });
});

describe('clampSecondPanelPixels', () => {
  const limits = { totalPixels: 800, minFirstPixels: 160, minSecondPixels: 96 };

  it('keeps a size between the limits', () => {
    expect(clampSecondPanelPixels(300, limits)).toBe(300);
  });

  it('keeps the minimum height of each panel', () => {
    expect(clampSecondPanelPixels(10, limits)).toBe(96);
    expect(clampSecondPanelPixels(790, limits)).toBe(640);
  });

  it('keeps the minimum of the second panel when the area is too small for both', () => {
    expect(clampSecondPanelPixels(300, { ...limits, totalPixels: 200 })).toBe(96);
  });
});

describe('readPanelSplitLayout', () => {
  const defaults = { mode: 'split' as const, secondPixels: 240 };

  it('reads a stored layout', () => {
    expect(readPanelSplitLayout({ mode: 'first-maximized', secondPixels: 300 }, defaults)).toEqual({
      mode: 'first-maximized',
      secondPixels: 300,
    });
  });

  it('uses the defaults for a missing or a damaged value', () => {
    expect(readPanelSplitLayout(null, defaults)).toEqual(defaults);
    expect(readPanelSplitLayout({ mode: 'sideways', secondPixels: 'x' }, defaults)).toEqual(defaults);
  });
});
