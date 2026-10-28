// The state of the strategy workbench (spec #99, ticket #106): the order of the results panel and the editor panel,
// the result tabs (one for each backtest of the strategy, then Trades, Orders, and Logs), the backtest that opens when
// it ends, and the toolbar shortcuts.
import { formatPercent, isFinalStatus, type Backtest } from '#lib/backtest';
import type { ForwardTest } from '#lib/forward_test';
import type { PanelSpec } from '#lib/foundation/workbench';

export type PaneOrder = 'results-on-top' | 'editor-on-top';
export type ResultTab = `backtest-${string}` | 'trades' | 'orders' | 'logs';
export type WorkbenchShortcut = 'save' | 'backtest' | 'forward-test';

export interface ResultTabItem {
  value: ResultTab;
  /** The full text of the tab: the name and the total return. */
  label: string;
  name: string;
  /** The backtest of a backtest tab; null for Trades, Orders, and Logs. */
  backtestId: number | null;
  /** The total return of a finished backtest, for ChangeText. */
  change: number | null;
  changeText: string;
}

/** The tab that shows and the backtest that Trades, Orders, and Logs show. */
export interface ResultSelection {
  tab: ResultTab | null;
  backtestId: number | null;
}

export const PANE_ORDER_STORAGE_KEY = 'atrade.strategy-page.pane-order';
const SPLITTER_LABEL = 'Resize the results and the editor';
const TABLE_TABS: ResultTabItem[] = [
  { value: 'trades', label: 'Trades', name: 'Trades', backtestId: null, change: null, changeText: '' },
  { value: 'orders', label: 'Orders', name: 'Orders', backtestId: null, change: null, changeText: '' },
  { value: 'logs', label: 'Logs', name: 'Logs', backtestId: null, change: null, changeText: '' },
];

/** The toolbar shortcuts as CodeMirror key names. The editor and its language server client use none of them. */
export const EDITOR_SHORTCUT_KEYS: Record<WorkbenchShortcut, string> = {
  save: 'Mod-s',
  backtest: 'Mod-b',
  'forward-test': 'Mod-Shift-f',
};

const SHORTCUT_KEY_TEXT: Record<WorkbenchShortcut, string> = { save: 'S', backtest: 'B', 'forward-test': 'Shift+F' };

/** The shortcut text of a tooltip. The shortcuts use Cmd on macOS and Ctrl elsewhere, like CodeMirror "Mod". */
export function describeShortcut(shortcut: WorkbenchShortcut, isMac: boolean): string {
  return `${isMac ? 'Cmd' : 'Ctrl'}+${SHORTCUT_KEY_TEXT[shortcut]}`;
}

/** The platform of the browser for the shortcuts, like CodeMirror. */
export function isMacPlatform(navigatorObject: Pick<Navigator, 'platform'>): boolean {
  return /Mac|iPhone|iPad/.test(navigatorObject.platform);
}

export function readPaneOrder(stored: unknown): PaneOrder {
  return stored === 'editor-on-top' ? 'editor-on-top' : 'results-on-top';
}

export function swapPaneOrder(order: PaneOrder): PaneOrder {
  return order === 'results-on-top' ? 'editor-on-top' : 'results-on-top';
}

/** The panels from top to bottom. Each panel has a height, because the swap can make each one the lower panel. */
export function listWorkbenchPanels(order: PaneOrder): PanelSpec[] {
  const results: PanelSpec = { id: 'results', minPixels: 160, defaultPixels: 320, splitterLabel: SPLITTER_LABEL };
  const editor: PanelSpec = { id: 'editor', minPixels: 128, defaultPixels: 320, splitterLabel: SPLITTER_LABEL };
  return order === 'results-on-top' ? [results, editor] : [editor, results];
}

/** The swap button: its arrow points to the place that the editor moves to. */
export function describeSwapButton(order: PaneOrder): { label: string; direction: 'up' | 'down' } {
  return order === 'results-on-top'
    ? { label: 'Put editor on top', direction: 'up' }
    : { label: 'Put editor at bottom', direction: 'down' };
}

export function createBacktestTab(backtestId: number): ResultTab {
  return `backtest-${String(backtestId)}`;
}

/** The backtests of the strategy, the newest first. */
export function selectStrategyBacktests(backtests: readonly Backtest[], strategyId: number | null): Backtest[] {
  return backtests.filter((backtest) => backtest.strategy_id === strategyId).sort((first, second) => second.id - first.id);
}

export function listResultTabs(backtests: readonly Backtest[], strategyId: number | null): ResultTabItem[] {
  const backtestTabs = selectStrategyBacktests(backtests, strategyId).map((backtest): ResultTabItem => {
    const name = `Backtest #${String(backtest.id)}`;
    if (backtest.metrics === null) {
      return { value: createBacktestTab(backtest.id), label: name, name, backtestId: backtest.id, change: null, changeText: '' };
    }
    const changeText = formatPercent(backtest.metrics.total_return_percent);
    return {
      value: createBacktestTab(backtest.id),
      label: `${name} ${changeText}`,
      name,
      backtestId: backtest.id,
      change: Number(backtest.metrics.total_return_percent),
      changeText,
    };
  });
  return [...backtestTabs, ...TABLE_TABS];
}

/**
 * The tab and the backtest that show. Without a selection, or when the selected backtest is not of the strategy, the
 * newest backtest shows. Trades, Orders, and Logs show the last selected backtest.
 */
export function resolveResultTab(
  selection: ResultSelection,
  backtests: readonly Backtest[],
  strategyId: number | null,
): { tab: ResultTab; backtestId: number | null } {
  const strategyBacktests = selectStrategyBacktests(backtests, strategyId);
  const isKnown = strategyBacktests.some((backtest) => backtest.id === selection.backtestId);
  const backtestId = isKnown ? selection.backtestId : (strategyBacktests[0]?.id ?? null);
  const isTableTab = TABLE_TABS.some((tab) => tab.value === selection.tab);
  const isShownBacktestTab = backtestId !== null && selection.tab === createBacktestTab(backtestId);
  if (selection.tab !== null && (isTableTab || isShownBacktestTab)) {
    return { tab: selection.tab, backtestId };
  }
  return { tab: backtestId === null ? 'trades' : createBacktestTab(backtestId), backtestId };
}

/** A backtest of the strategy that was not final in the previous list and is final in the next list. */
export function findFinishedBacktest(
  previous: readonly Backtest[],
  next: readonly Backtest[],
  strategyId: number | null,
): Backtest | null {
  const wasRunning = new Set(previous.filter((backtest) => !isFinalStatus(backtest.status)).map((backtest) => backtest.id));
  return (
    next.find((backtest) => backtest.strategy_id === strategyId && isFinalStatus(backtest.status) && wasRunning.has(backtest.id)) ??
    null
  );
}

/** The newest forward test of the strategy with the desired state running: the Stop forward test button stops it. */
export function findRunningForwardTest(forwardTests: readonly ForwardTest[], strategyId: number | null): ForwardTest | null {
  return forwardTests
    .filter((forwardTest) => forwardTest.strategy_id === strategyId && forwardTest.desired_state === 'running')
    .reduce<ForwardTest | null>((newest, forwardTest) => (newest === null || forwardTest.id > newest.id ? forwardTest : newest), null);
}

/** Ctrl (Cmd on macOS) with S, B, or Shift F. Alt and other keys are not a shortcut. */
export function readWorkbenchShortcut(
  event: Pick<KeyboardEvent, 'key' | 'ctrlKey' | 'metaKey' | 'shiftKey' | 'altKey'>,
  isMac: boolean,
): WorkbenchShortcut | null {
  const hasMod = isMac ? event.metaKey && !event.ctrlKey : event.ctrlKey && !event.metaKey;
  if (!hasMod || event.altKey) {
    return null;
  }
  const key = event.key.toLowerCase();
  if (event.shiftKey) {
    return key === 'f' ? 'forward-test' : null;
  }
  if (key === 's') {
    return 'save';
  }
  return key === 'b' ? 'backtest' : null;
}
