// The state of stacked workbench panels (PanelSplit), from top to bottom.
//  - Minimized: the panel shows only its header line (or its status bar). Several panels can be minimized, but one
//    panel always stays open.
//  - Maximized: the panel gets all the height. The other panels show only their header lines, so they can be restored.
//    One panel at a time is maximized.
//  - The first open panel fills the rest of the height. Each other open panel has its own height in pixels, and the
//    splitter above it changes that height. A splitter shows only between 2 open panels and while no panel is
//    maximized.

/**
 * A panel of a PanelSplit. The first panel has no `defaultPixels`: it fills the rest of the height. `splitterLabel`
 * names the splitter above the panel (not used for the first panel). `startsMinimized` minimizes the panel in the
 * default layout, for example a panel with a status bar.
 */
export interface PanelSpec {
  id: string;
  minPixels: number;
  defaultPixels?: number;
  splitterLabel?: string;
  startsMinimized?: boolean;
}

/** The size of one panel, for its Minimize and Maximize buttons. */
export type PanelSize = 'normal' | 'minimized' | 'maximized';

export interface PanelSplitLayout {
  maximized: string | null;
  minimized: string[];
  /** The height of each panel that has one (all but the first panel). */
  pixels: Record<string, number>;
}

export type PanelRow = { kind: 'panel'; id: string; track: string } | { kind: 'splitter'; id: string };

export interface PixelRange {
  min: number;
  max: number;
}

const FILL_TRACK = 'minmax(0, 1fr)';

export function createPanelSplitLayout(specs: readonly PanelSpec[]): PanelSplitLayout {
  const pixels: Record<string, number> = {};
  for (const spec of specs) {
    if (spec.defaultPixels !== undefined) {
      pixels[spec.id] = spec.defaultPixels;
    }
  }
  const minimized = specs.filter((spec) => spec.startsMinimized === true).map((spec) => spec.id);
  return { maximized: null, minimized: minimized.length >= specs.length ? minimized.slice(0, -1) : minimized, pixels };
}

export function isPanelHeaderOnly(layout: PanelSplitLayout, id: string): boolean {
  return layout.minimized.includes(id) || (layout.maximized !== null && layout.maximized !== id);
}

export function findPanelSize(layout: PanelSplitLayout, id: string): PanelSize {
  if (layout.maximized === id) {
    return 'maximized';
  }
  return layout.minimized.includes(id) ? 'minimized' : 'normal';
}

/**
 * A Minimize or Maximize button: the first click sets the size, a second click restores the panel. Maximize opens the
 * minimized panels again. Minimize ends a maximize. The last open panel does not minimize.
 */
export function togglePanelSize(
  layout: PanelSplitLayout,
  specs: readonly PanelSpec[],
  id: string,
  size: 'minimized' | 'maximized',
): PanelSplitLayout {
  if (size === 'maximized') {
    return { ...layout, maximized: layout.maximized === id ? null : id, minimized: [] };
  }
  if (layout.minimized.includes(id)) {
    return { ...layout, minimized: layout.minimized.filter((minimizedId) => minimizedId !== id) };
  }
  const minimized = specs.map((spec) => spec.id).filter((specId) => specId === id || layout.minimized.includes(specId));
  if (minimized.length >= specs.length) {
    return layout;
  }
  return { ...layout, maximized: null, minimized };
}

/**
 * Opens a panel that shows only its header line (or its status bar): it is no longer minimized, and another panel is
 * no longer maximized. An open panel keeps its size.
 */
export function openPanel(layout: PanelSplitLayout, id: string): PanelSplitLayout {
  if (!isPanelHeaderOnly(layout, id)) {
    return layout;
  }
  return { ...layout, maximized: null, minimized: layout.minimized.filter((minimizedId) => minimizedId !== id) };
}

/** Escape restores a maximized panel. A minimized panel stays minimized. */
export function restorePanelSplit(layout: PanelSplitLayout): PanelSplitLayout {
  return layout.maximized === null ? layout : { ...layout, maximized: null };
}

function findFillPanelId(layout: PanelSplitLayout, specs: readonly PanelSpec[]): string | undefined {
  return specs.find((spec) => !isPanelHeaderOnly(layout, spec.id))?.id;
}

/** The rows of the panel area in order: the panels and the splitters, each panel with its CSS grid track. */
export function listPanelRows(
  layout: PanelSplitLayout,
  specs: readonly PanelSpec[],
  pixels: Record<string, number> = layout.pixels,
): PanelRow[] {
  const fillId = findFillPanelId(layout, specs);
  const rows: PanelRow[] = [];
  specs.forEach((spec, index) => {
    const isOpen = !isPanelHeaderOnly(layout, spec.id);
    const previous = specs[index - 1];
    if (isOpen && spec.id !== fillId && previous !== undefined && !isPanelHeaderOnly(layout, previous.id)) {
      rows.push({ kind: 'splitter', id: spec.id });
    }
    let track = 'auto';
    if (spec.id === fillId) {
      track = FILL_TRACK;
    } else if (isOpen) {
      track = `${String(pixels[spec.id] ?? spec.defaultPixels ?? spec.minPixels)}px`;
    }
    rows.push({ kind: 'panel', id: spec.id, track });
  });
  return rows;
}

/** The heights that the splitter above a panel can give it: the fill panel and the other open panels keep theirs. */
export function findPanelPixelRange(
  layout: PanelSplitLayout,
  specs: readonly PanelSpec[],
  id: string,
  totalPixels: number,
): PixelRange {
  const spec = specs.find((candidate) => candidate.id === id);
  const min = spec?.minPixels ?? 0;
  const fillId = findFillPanelId(layout, specs);
  let reservedPixels = 0;
  for (const other of specs) {
    if (other.id === id || isPanelHeaderOnly(layout, other.id)) {
      continue;
    }
    reservedPixels += other.id === fillId ? other.minPixels : (layout.pixels[other.id] ?? other.minPixels);
  }
  return { min, max: Math.max(min, totalPixels - reservedPixels) };
}

/** A stored layout from the browser storage. A missing, damaged, or unknown value gives the defaults. */
export function readPanelSplitLayout(stored: unknown, specs: readonly PanelSpec[]): PanelSplitLayout {
  const defaults = createPanelSplitLayout(specs);
  if (typeof stored !== 'object' || stored === null) {
    return defaults;
  }
  const layout = stored as Partial<Record<keyof PanelSplitLayout, unknown>>;
  const ids = specs.map((spec) => spec.id);
  const maximized = ids.find((id) => id === layout.maximized) ?? null;
  const minimized = maximized === null ? readMinimized(layout.minimized, ids) : [];
  return { maximized, minimized, pixels: readPixels(layout.pixels, defaults.pixels) };
}

// Known panels only, and one panel stays open.
function readMinimized(stored: unknown, ids: readonly string[]): string[] {
  const storedIds: unknown[] = Array.isArray(stored) ? stored : [];
  const minimized = ids.filter((id) => storedIds.includes(id));
  return minimized.length >= ids.length ? minimized.slice(0, -1) : minimized;
}

function readPixels(stored: unknown, defaults: Record<string, number>): Record<string, number> {
  const pixels = { ...defaults };
  if (typeof stored !== 'object' || stored === null) {
    return pixels;
  }
  for (const id of Object.keys(pixels)) {
    const value: unknown = Reflect.get(stored, id);
    if (typeof value === 'number' && Number.isFinite(value)) {
      pixels[id] = value;
    }
  }
  return pixels;
}
