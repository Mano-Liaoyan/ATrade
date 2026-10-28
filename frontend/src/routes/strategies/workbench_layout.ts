// PROTOTYPE (#99), throwaway: the pane order, the splitter position, and the drawdown of the strategy workbench.
import type { EquityPoint } from '#lib/backtest';

export type ResultsTab = `backtest-${string}` | 'trades' | 'orders' | 'logs';
export type OutputTab = 'problems' | 'output';
export type IconTone = 'neutral' | 'interactive' | 'success' | 'warning' | 'error';

export function backtestTab(backtestId: number): ResultsTab {
  return `backtest-${String(backtestId)}`;
}

export type PaneOrder = 'results-on-top' | 'editor-on-top';

const PANE_ORDER_KEY = 'atrade.prototype99.strategy-pane-order';
const PERCENT = 100;
// The splitter keeps each pane at least this part of the height.
const MIN_PANE_FRACTION = 0.15;
export const DEFAULT_TOP_FRACTION = 0.5;

export function readPaneOrder(storage: () => Storage): PaneOrder {
  try {
    return storage().getItem(PANE_ORDER_KEY) === 'editor-on-top' ? 'editor-on-top' : 'results-on-top';
  } catch {
    return 'results-on-top';
  }
}

export function writePaneOrder(storage: () => Storage, order: PaneOrder): void {
  try {
    storage().setItem(PANE_ORDER_KEY, order);
  } catch {
    // The browser blocks storage, for example in a private window. The order then lasts only for this page.
  }
}

export function clampTopFraction(fraction: number): number {
  return Math.min(1 - MIN_PANE_FRACTION, Math.max(MIN_PANE_FRACTION, fraction));
}

export interface DrawdownPoint {
  time_utc: string;
  drawdown_percent: number;
}

// The drawdown at each point: the fall from the highest equity before it, as a negative percent.
export function computeDrawdown(points: readonly EquityPoint[]): DrawdownPoint[] {
  let highestEquity = Number.NEGATIVE_INFINITY;
  return points.map((point) => {
    const equity = Number(point.equity_usd);
    highestEquity = Math.max(highestEquity, equity);
    const drawdownPercent = highestEquity > 0 ? (equity / highestEquity - 1) * PERCENT : 0;
    return { time_utc: point.time_utc, drawdown_percent: drawdownPercent };
  });
}

// A panel is normal, minimized to its tab line, or maximized to the whole main area below the toolbar.
// The output panel is minimized by default: then only the status bar shows.
export type PanelSize = 'normal' | 'minimized' | 'maximized';
export type PanelId = 'results' | 'editor' | 'output';
export type PanelSizes = Record<PanelId, PanelSize>;

const PANEL_SIZES_KEY = 'atrade.prototype99.strategy-panel-sizes';
const DEFAULT_PANEL_SIZES: PanelSizes = { results: 'normal', editor: 'normal', output: 'minimized' };
const PANEL_IDS: readonly PanelId[] = ['results', 'editor', 'output'];
const PANEL_SIZE_VALUES: readonly string[] = ['normal', 'minimized', 'maximized'];

function readPanelSize(stored: Record<string, unknown>, id: PanelId): PanelSize {
  const value = stored[id];
  return typeof value === 'string' && PANEL_SIZE_VALUES.includes(value) ? (value as PanelSize) : DEFAULT_PANEL_SIZES[id];
}

export function readPanelSizes(storage: () => Storage): PanelSizes {
  try {
    const stored: unknown = JSON.parse(storage().getItem(PANEL_SIZES_KEY) ?? '{}');
    if (typeof stored !== 'object' || stored === null) {
      return { ...DEFAULT_PANEL_SIZES };
    }
    const record = stored as Record<string, unknown>;
    return { results: readPanelSize(record, 'results'), editor: readPanelSize(record, 'editor'), output: readPanelSize(record, 'output') };
  } catch {
    return { ...DEFAULT_PANEL_SIZES };
  }
}

export function writePanelSizes(storage: () => Storage, sizes: PanelSizes): void {
  try {
    storage().setItem(PANEL_SIZES_KEY, JSON.stringify(sizes));
  } catch {
    // The browser blocks storage. The sizes then last only for this page.
  }
}

export function findMaximizedPanel(sizes: PanelSizes): PanelId | null {
  return PANEL_IDS.find((id) => sizes[id] === 'maximized') ?? null;
}

// A collapsed panel shows only its tab line (the output panel: only the status bar).
export function isPanelCollapsed(sizes: PanelSizes, id: PanelId): boolean {
  const maximized = findMaximizedPanel(sizes);
  return sizes[id] === 'minimized' || (maximized !== null && maximized !== id);
}

export function toggleMinimized(sizes: PanelSizes, id: PanelId): PanelSizes {
  return { ...sizes, [id]: sizes[id] === 'minimized' ? 'normal' : 'minimized' };
}

// Only one panel is maximized at a time.
export function toggleMaximized(sizes: PanelSizes, id: PanelId): PanelSizes {
  if (sizes[id] === 'maximized') {
    return { ...sizes, [id]: 'normal' };
  }
  const restored = restoreMaximized(sizes);
  return { ...restored, [id]: 'maximized' };
}

export function restoreMaximized(sizes: PanelSizes): PanelSizes {
  const maximized = findMaximizedPanel(sizes);
  return maximized === null ? sizes : { ...sizes, [maximized]: 'normal' };
}

// Opens the output panel above the status bar. A maximized output panel stays maximized.
export function openOutputPanel(sizes: PanelSizes): PanelSizes {
  const restored = sizes.output === 'maximized' ? sizes : restoreMaximized(sizes);
  return { ...restored, output: sizes.output === 'maximized' ? 'maximized' : 'normal' };
}
