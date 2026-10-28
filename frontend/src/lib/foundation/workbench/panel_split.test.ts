// The state of stacked workbench panels: minimize, maximize, restore, the splitters, and the stored layout.
import { describe, expect, it } from 'vite-plus/test';
import {
  createPanelSplitLayout,
  findPanelPixelRange,
  findPanelSize,
  isPanelHeaderOnly,
  listPanelRows,
  openPanel,
  readPanelSplitLayout,
  restorePanelSplit,
  togglePanelSize,
  type PanelSpec,
} from './index';

const TWO: PanelSpec[] = [
  { id: 'chart', minPixels: 160 },
  { id: 'account', minPixels: 96, defaultPixels: 240 },
];
const THREE: PanelSpec[] = [
  { id: 'results', minPixels: 160 },
  { id: 'editor', minPixels: 160, defaultPixels: 300 },
  { id: 'output', minPixels: 96, defaultPixels: 160 },
];

describe('createPanelSplitLayout', () => {
  it('opens all panels with their default heights', () => {
    expect(createPanelSplitLayout(THREE)).toEqual({ maximized: null, minimized: [], pixels: { editor: 300, output: 160 } });
  });
});

describe('a panel that starts minimized', () => {
  const WITH_OUTPUT: PanelSpec[] = [
    { id: 'results', minPixels: 160 },
    { id: 'output', minPixels: 96, defaultPixels: 240, startsMinimized: true },
  ];

  it('is minimized in the default layout and when no layout is stored', () => {
    expect(createPanelSplitLayout(WITH_OUTPUT).minimized).toEqual(['output']);
    expect(readPanelSplitLayout(null, WITH_OUTPUT).minimized).toEqual(['output']);
  });

  it('stays open when the stored layout opened it', () => {
    expect(readPanelSplitLayout({ maximized: null, minimized: [], pixels: {} }, WITH_OUTPUT).minimized).toEqual([]);
  });
});

describe('openPanel', () => {
  it('opens a minimized panel and keeps the other sizes', () => {
    const layout = { maximized: null, minimized: ['editor', 'output'], pixels: {} };

    expect(openPanel(layout, 'output')).toEqual({ maximized: null, minimized: ['editor'], pixels: {} });
  });

  it('ends the maximize of another panel, and keeps a maximized panel maximized', () => {
    expect(openPanel({ maximized: 'results', minimized: [], pixels: {} }, 'output').maximized).toBeNull();
    expect(openPanel({ maximized: 'output', minimized: [], pixels: {} }, 'output').maximized).toBe('output');
  });
});

describe('togglePanelSize', () => {
  it('minimizes a panel and restores it with a second click', () => {
    const minimized = togglePanelSize(createPanelSplitLayout(TWO), TWO, 'account', 'minimized');

    expect(findPanelSize(minimized, 'account')).toBe('minimized');
    expect(findPanelSize(togglePanelSize(minimized, TWO, 'account', 'minimized'), 'account')).toBe('normal');
  });

  it('maximizes a panel and restores the others, also a minimized one', () => {
    const minimized = togglePanelSize(createPanelSplitLayout(TWO), TWO, 'account', 'minimized');
    const maximized = togglePanelSize(minimized, TWO, 'chart', 'maximized');

    expect(findPanelSize(maximized, 'chart')).toBe('maximized');
    expect(findPanelSize(maximized, 'account')).toBe('normal');
    expect(findPanelSize(togglePanelSize(maximized, TWO, 'chart', 'maximized'), 'chart')).toBe('normal');
  });

  it('keeps one panel open: the last open panel does not minimize', () => {
    const minimized = togglePanelSize(createPanelSplitLayout(TWO), TWO, 'account', 'minimized');

    expect(togglePanelSize(minimized, TWO, 'chart', 'minimized')).toEqual(minimized);
  });

  it('minimizes 2 of 3 panels', () => {
    let layout = togglePanelSize(createPanelSplitLayout(THREE), THREE, 'results', 'minimized');
    layout = togglePanelSize(layout, THREE, 'output', 'minimized');

    expect(layout.minimized).toEqual(['results', 'output']);
  });
});

describe('isPanelHeaderOnly', () => {
  it('shows only the header of a minimized panel and of the panels beside a maximized panel', () => {
    const minimized = togglePanelSize(createPanelSplitLayout(TWO), TWO, 'chart', 'minimized');
    const maximized = togglePanelSize(createPanelSplitLayout(THREE), THREE, 'editor', 'maximized');

    expect(isPanelHeaderOnly(minimized, 'chart')).toBe(true);
    expect(isPanelHeaderOnly(minimized, 'account')).toBe(false);
    expect(['results', 'editor', 'output'].map((id) => isPanelHeaderOnly(maximized, id))).toEqual([true, false, true]);
  });
});

describe('restorePanelSplit', () => {
  it('restores a maximized panel and keeps a minimized panel', () => {
    const maximized = togglePanelSize(createPanelSplitLayout(TWO), TWO, 'chart', 'maximized');
    const minimized = togglePanelSize(createPanelSplitLayout(TWO), TWO, 'chart', 'minimized');

    expect(restorePanelSplit(maximized).maximized).toBeNull();
    expect(restorePanelSplit(minimized)).toEqual(minimized);
  });
});

describe('listPanelRows', () => {
  it('gives the first panel the rest of the height and puts a splitter before each panel with a height', () => {
    const rows = listPanelRows(createPanelSplitLayout(THREE), THREE);

    expect(rows).toEqual([
      { kind: 'panel', id: 'results', track: 'minmax(0, 1fr)' },
      { kind: 'splitter', id: 'editor' },
      { kind: 'panel', id: 'editor', track: '300px' },
      { kind: 'splitter', id: 'output' },
      { kind: 'panel', id: 'output', track: '160px' },
    ]);
  });

  it('gives the rest of the height to the first open panel and hides the splitters beside a minimized panel', () => {
    const layout = togglePanelSize(createPanelSplitLayout(THREE), THREE, 'results', 'minimized');

    expect(listPanelRows(layout, THREE)).toEqual([
      { kind: 'panel', id: 'results', track: 'auto' },
      { kind: 'panel', id: 'editor', track: 'minmax(0, 1fr)' },
      { kind: 'splitter', id: 'output' },
      { kind: 'panel', id: 'output', track: '160px' },
    ]);
  });

  it('has no splitter while a panel is maximized', () => {
    const layout = togglePanelSize(createPanelSplitLayout(TWO), TWO, 'account', 'maximized');

    expect(listPanelRows(layout, TWO)).toEqual([
      { kind: 'panel', id: 'chart', track: 'auto' },
      { kind: 'panel', id: 'account', track: 'minmax(0, 1fr)' },
    ]);
  });
});

describe('findPanelPixelRange', () => {
  const layout = createPanelSplitLayout(THREE);

  it('keeps the minimum of the panel and leaves the minimum of the fill panel and the other heights', () => {
    expect(findPanelPixelRange(layout, THREE, 'output', 1000)).toEqual({ min: 96, max: 1000 - 160 - 300 });
  });

  it('gives the minimum as the maximum when the area is too small', () => {
    expect(findPanelPixelRange(layout, THREE, 'output', 300)).toEqual({ min: 96, max: 96 });
  });
});

describe('readPanelSplitLayout', () => {
  it('reads a stored layout', () => {
    const stored = { maximized: 'chart', minimized: [], pixels: { account: 300 } };

    expect(readPanelSplitLayout(stored, TWO)).toEqual(stored);
  });

  it('uses the defaults for a missing or a damaged value and for unknown panels', () => {
    expect(readPanelSplitLayout(null, TWO)).toEqual(createPanelSplitLayout(TWO));
    expect(readPanelSplitLayout({ maximized: 'sideways', minimized: ['x'], pixels: { account: 'x' } }, TWO)).toEqual(
      createPanelSplitLayout(TWO),
    );
  });

  it('opens a panel when the stored layout minimizes all panels', () => {
    expect(readPanelSplitLayout({ maximized: null, minimized: ['chart', 'account'], pixels: {} }, TWO).minimized).toEqual([
      'chart',
    ]);
  });
});
