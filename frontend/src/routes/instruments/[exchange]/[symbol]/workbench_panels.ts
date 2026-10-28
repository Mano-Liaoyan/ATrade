// PROTOTYPE (#99), throwaway: the panel layout of the instrument workbench, kept in localStorage.
//  - The center column has the chart panel and the account panel. One of them can be minimized or maximized.
//  - The watchlist column and the order column can collapse to a rail.

export type CenterPanel = 'chart' | 'account';
export type CenterMode = 'split' | `${CenterPanel}-minimized` | `${CenterPanel}-maximized`;

export interface PanelLayout {
  center: CenterMode;
  accountPanelPixels: number;
  isWatchlistCollapsed: boolean;
  isOrderPanelCollapsed: boolean;
}

const STORAGE_KEY = 'atrade.prototype-99.instrument-workbench';
const CENTER_MODES: readonly CenterMode[] = [
  'split',
  'chart-minimized',
  'chart-maximized',
  'account-minimized',
  'account-maximized',
];

export const DEFAULT_PANEL_LAYOUT: PanelLayout = {
  center: 'split',
  accountPanelPixels: 240,
  isWatchlistCollapsed: false,
  isOrderPanelCollapsed: false,
};

export function readPanelLayout(): PanelLayout {
  try {
    const stored: unknown = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? 'null');
    if (typeof stored !== 'object' || stored === null) {
      return DEFAULT_PANEL_LAYOUT;
    }
    const layout = stored as Partial<Record<keyof PanelLayout, unknown>>;
    return {
      center: CENTER_MODES.find((mode) => mode === layout.center) ?? DEFAULT_PANEL_LAYOUT.center,
      accountPanelPixels:
        typeof layout.accountPanelPixels === 'number' ? layout.accountPanelPixels : DEFAULT_PANEL_LAYOUT.accountPanelPixels,
      isWatchlistCollapsed: layout.isWatchlistCollapsed === true,
      isOrderPanelCollapsed: layout.isOrderPanelCollapsed === true,
    };
  } catch {
    return DEFAULT_PANEL_LAYOUT;
  }
}

export function writePanelLayout(layout: PanelLayout): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(layout));
  } catch {
    // Private windows and blocked storage: the layout is not kept.
  }
}

// A panel shows only its header line when it is minimized, or when the other panel is maximized.
export function isHeaderOnly(center: CenterMode, panel: CenterPanel): boolean {
  const otherPanel: CenterPanel = panel === 'chart' ? 'account' : 'chart';
  return center === `${panel}-minimized` || center === `${otherPanel}-maximized`;
}

// The minimize and maximize buttons toggle: a second click restores the split.
export function toggleCenterMode(center: CenterMode, panel: CenterPanel, action: 'minimized' | 'maximized'): CenterMode {
  const mode: CenterMode = `${panel}-${action}`;
  return center === mode ? 'split' : mode;
}

// Double-click on an empty part of a header line: only the header itself, not its buttons, tabs, or switchers.
export function isEmptyHeaderTarget(target: EventTarget | null, header: HTMLElement): boolean {
  if (!(target instanceof Element) || !header.contains(target)) {
    return false;
  }
  return target.closest('button, a, input, [role="tab"], [role="tablist"] button, [role="tabpanel"]') === null;
}
