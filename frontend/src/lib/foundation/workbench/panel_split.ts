// The state of two stacked workbench panels (PanelSplit). One panel at a time can be minimized or maximized.
//  - Minimized: the panel shows only its header line. The other panel gets the rest of the height.
//  - Maximized: the panel gets all the height. The other panel shows only its header line, so it can be restored.
//  - Split: both panels show, with the splitter between them. The splitter sets the height of the second panel.

export type PanelPosition = 'first' | 'second';
export type PanelSplitMode = 'split' | `${PanelPosition}-minimized` | `${PanelPosition}-maximized`;
/** The size of one panel, for its Minimize and Maximize buttons. */
export type PanelSize = 'normal' | 'minimized' | 'maximized';

export interface PanelSplitLayout {
  mode: PanelSplitMode;
  secondPixels: number;
}

export interface PanelSplitLimits {
  totalPixels: number;
  minFirstPixels: number;
  minSecondPixels: number;
}

const PANEL_SPLIT_MODES: readonly PanelSplitMode[] = [
  'split',
  'first-minimized',
  'first-maximized',
  'second-minimized',
  'second-maximized',
];

function findOtherPanel(position: PanelPosition): PanelPosition {
  return position === 'first' ? 'second' : 'first';
}

/** A Minimize or Maximize button: the first click sets the size, a second click restores the split. */
export function togglePanelSize(
  mode: PanelSplitMode,
  position: PanelPosition,
  size: 'minimized' | 'maximized',
): PanelSplitMode {
  const newMode: PanelSplitMode = `${position}-${size}`;
  return mode === newMode ? 'split' : newMode;
}

export function findPanelSize(mode: PanelSplitMode, position: PanelPosition): PanelSize {
  if (mode === `${position}-minimized`) {
    return 'minimized';
  }
  if (mode === `${position}-maximized`) {
    return 'maximized';
  }
  return 'normal';
}

export function isPanelHeaderOnly(mode: PanelSplitMode, position: PanelPosition): boolean {
  return mode === `${position}-minimized` || mode === `${findOtherPanel(position)}-maximized`;
}

/** Escape restores a maximized panel. A minimized panel stays minimized. */
export function restorePanelSplit(mode: PanelSplitMode): PanelSplitMode {
  return mode.endsWith('-maximized') ? 'split' : mode;
}

/** The CSS grid rows of the panel area: first panel, splitter, second panel. Without a split, there is no splitter. */
export function formatPanelRows(mode: PanelSplitMode, secondPixels: number): string {
  if (mode === 'split') {
    return `minmax(0, 1fr) auto ${String(secondPixels)}px`;
  }
  return isPanelHeaderOnly(mode, 'first') ? 'auto minmax(0, 1fr)' : 'minmax(0, 1fr) auto';
}

/** Each panel keeps its minimum height. When the area is too small for both, the second panel keeps its minimum. */
export function clampSecondPanelPixels(secondPixels: number, limits: PanelSplitLimits): number {
  const maxSecondPixels = Math.max(limits.minSecondPixels, limits.totalPixels - limits.minFirstPixels);
  return Math.min(Math.max(secondPixels, limits.minSecondPixels), maxSecondPixels);
}

/** A stored layout from the browser storage. A missing or damaged value gives the defaults. */
export function readPanelSplitLayout(stored: unknown, defaults: PanelSplitLayout): PanelSplitLayout {
  if (typeof stored !== 'object' || stored === null) {
    return defaults;
  }
  const layout = stored as Partial<Record<keyof PanelSplitLayout, unknown>>;
  const secondPixels = layout.secondPixels;
  return {
    mode: PANEL_SPLIT_MODES.find((mode) => mode === layout.mode) ?? defaults.mode,
    secondPixels: typeof secondPixels === 'number' && Number.isFinite(secondPixels) ? secondPixels : defaults.secondPixels,
  };
}
