// The state of the strategy workbench (spec #99, tickets #106 and #107): the order of the results panel and the editor
// panel, the problems and output panel below them, the result tabs (one for each backtest of the strategy that the user
// did not close, then the fixed Trades, Orders, and Logs), the backtest that opens when it ends, the output lines, and
// the toolbar shortcuts.
import { formatPercent, isFinalStatus, type Backtest, type BacktestStatus } from '#lib/backtest';
import type { ForwardTest } from '#lib/forward_test';
import type { PanelSpec } from '#lib/foundation/workbench';
import type { CodeProblem, StrategyVersionSummary } from '#lib/strategy';

export type PaneOrder = 'results-on-top' | 'editor-on-top';
export type ResultTab = `backtest-${string}` | 'trades' | 'orders' | 'logs';
export type WorkbenchShortcut = 'save' | 'backtest' | 'forward-test';
export type OutputTab = 'problems' | 'output';

export interface ResultTabItem {
  value: ResultTab;
  /** The full text of the tab: the name and the total return. */
  label: string;
  name: string;
  /** The backtest of a backtest tab; null for Trades, Orders, and Logs. */
  backtestId: number | null;
  /** The status of the backtest of a backtest tab, for its status icon; null for Trades, Orders, and Logs. */
  status: BacktestStatus | null;
  /** The total return of a finished backtest, for ChangeText. */
  change: number | null;
  changeText: string;
}

/** The tab that shows and the backtest that Trades, Orders, and Logs show. */
export interface ResultSelection {
  tab: ResultTab | null;
  backtestId: number | null;
}

/** The backtest tabs and the fixed tabs of the results panel. */
export interface ResultTabs {
  backtestTabs: ResultTabItem[];
  tableTabs: ResultTabItem[];
}

/** The closed backtest tabs of each strategy, by strategy ID. A closed tab is only hidden: the backtest stays. */
export type ClosedBacktestTabs = Record<string, number[]>;

export const PANE_ORDER_STORAGE_KEY = 'atrade.strategy-page.pane-order';
export const CLOSED_BACKTEST_TABS_STORAGE_KEY = 'atrade.strategy-page.closed-backtest-tabs';
const NO_CLOSED_TABS: ReadonlySet<number> = new Set();
const SPLITTER_LABEL = 'Resize the results and the editor';
const TABLE_TABS: ResultTabItem[] = [
  { value: 'trades', label: 'Trades', name: 'Trades', backtestId: null, status: null, change: null, changeText: '' },
  { value: 'orders', label: 'Orders', name: 'Orders', backtestId: null, status: null, change: null, changeText: '' },
  { value: 'logs', label: 'Logs', name: 'Logs', backtestId: null, status: null, change: null, changeText: '' },
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

const OUTPUT_PANEL: PanelSpec = {
  id: 'output',
  minPixels: 96,
  defaultPixels: 240,
  splitterLabel: 'Resize the problems and output',
  startsMinimized: true,
};

/**
 * The panels from top to bottom. The results and the editor each have a height, because the swap can make each one the
 * lower panel. The problems and output panel is always at the bottom; minimized, it is the 24px status bar.
 */
export function listWorkbenchPanels(order: PaneOrder): PanelSpec[] {
  const results: PanelSpec = { id: 'results', minPixels: 160, defaultPixels: 320, splitterLabel: SPLITTER_LABEL };
  const editor: PanelSpec = { id: 'editor', minPixels: 128, defaultPixels: 320, splitterLabel: SPLITTER_LABEL };
  return order === 'results-on-top' ? [results, editor, OUTPUT_PANEL] : [editor, results, OUTPUT_PANEL];
}

/** The counts of the status bar. The code checks give no severity, so each code problem is an error. */
export function describeProblemCounts(problems: readonly CodeProblem[]): { errors: number; warnings: number; label: string } {
  const errors = problems.length;
  const warnings = 0;
  return { errors, warnings, label: `Problems: ${String(errors)} errors, ${String(warnings)} warnings` };
}

/** A line of the Output tab: the UTC time (HH:MM:SS), then the text. */
export function createOutputLine(time: Date, text: string): string {
  return `${time.toISOString().slice('YYYY-MM-DDT'.length, 'YYYY-MM-DDTHH:MM:SS'.length)}  ${text}`;
}

/** The Output text of a backtest that starts or ends. A failed backtest gives its error message. */
export function describeBacktestEvent(backtest: Pick<Backtest, 'id' | 'status' | 'error_message'>): string {
  const name = `Backtest #${String(backtest.id)} ${backtest.status.replaceAll('_', ' ')}`;
  return backtest.error_message === null || backtest.error_message === '' ? `${name}.` : `${name}: ${backtest.error_message}`;
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

/** The backtests of the strategy whose tab the user did not close, the newest first. */
function selectOpenBacktests(
  backtests: readonly Backtest[],
  strategyId: number | null,
  closedIds: ReadonlySet<number>,
): Backtest[] {
  return selectStrategyBacktests(backtests, strategyId).filter((backtest) => !closedIds.has(backtest.id));
}

export function listResultTabs(
  backtests: readonly Backtest[],
  strategyId: number | null,
  closedIds: ReadonlySet<number> = NO_CLOSED_TABS,
): ResultTabs {
  const backtestTabs = selectOpenBacktests(backtests, strategyId, closedIds).map((backtest): ResultTabItem => {
    const name = `Backtest #${String(backtest.id)}`;
    const tab = { value: createBacktestTab(backtest.id), name, backtestId: backtest.id, status: backtest.status };
    if (backtest.metrics === null) {
      return { ...tab, label: name, change: null, changeText: '' };
    }
    const changeText = formatPercent(backtest.metrics.total_return_percent);
    return { ...tab, label: `${name} ${changeText}`, change: Number(backtest.metrics.total_return_percent), changeText };
  });
  return { backtestTabs, tableTabs: TABLE_TABS };
}

/** The stored closed tabs. A missing or damaged value gives no closed tabs; a wrong ID is left out. */
export function readClosedBacktestTabs(stored: unknown): ClosedBacktestTabs {
  if (typeof stored !== 'object' || stored === null || Array.isArray(stored)) {
    return {};
  }
  const closed: ClosedBacktestTabs = {};
  for (const [strategyKey, ids] of Object.entries(stored as Record<string, unknown>)) {
    if (Array.isArray(ids)) {
      closed[strategyKey] = ids.filter((id): id is number => Number.isInteger(id));
    }
  }
  return closed;
}

export function closeBacktestTab(closed: ClosedBacktestTabs, strategyId: number, backtestId: number): ClosedBacktestTabs {
  const strategyKey = String(strategyId);
  const ids = closed[strategyKey] ?? [];
  return ids.includes(backtestId) ? closed : { ...closed, [strategyKey]: [...ids, backtestId] };
}

export function findClosedBacktestIds(closed: ClosedBacktestTabs, strategyId: number | null): ReadonlySet<number> {
  return strategyId === null ? NO_CLOSED_TABS : new Set(closed[String(strategyId)] ?? []);
}

/** The message of "Ask AI to fix": the AI assistant reads the error itself with read_backtest. */
export function describeFixRequest(backtestId: number): string {
  return `Backtest #${String(backtestId)} failed. Read it with read_backtest and fix the strategy code.`;
}

/**
 * The tab and the backtest that show. Without a selection, or when the selected backtest is not of the strategy or its
 * tab is closed, the newest open backtest shows. Trades, Orders, and Logs show the last selected backtest.
 */
export function resolveResultTab(
  selection: ResultSelection,
  backtests: readonly Backtest[],
  strategyId: number | null,
  closedIds: ReadonlySet<number> = NO_CLOSED_TABS,
): { tab: ResultTab; backtestId: number | null } {
  const strategyBacktests = selectOpenBacktests(backtests, strategyId, closedIds);
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

/** A version in the version Select. A discarded version has the tag "Discarded" after its version number. */
export interface VersionItem {
  value: string;
  label: string;
  tag?: string;
}

type VersionFlags = Pick<StrategyVersionSummary, 'version_number' | 'discarded'>;

/** The items of the version Select (docs/architecture/assistant.md 25.5.3). Without "Show discarded versions", the
 * only discarded version in the list is the open version, so that the Select always names the open version. */
export function listVersionItems(
  versions: readonly VersionFlags[],
  { showDiscarded, openVersionNumber }: { showDiscarded: boolean; openVersionNumber: number | null },
): VersionItem[] {
  return versions
    .filter((version) => showDiscarded || !version.discarded || version.version_number === openVersionNumber)
    .map((version) => {
      const item = { value: String(version.version_number), label: `v${String(version.version_number)}` };
      return version.discarded ? { ...item, tag: 'Discarded' } : item;
    });
}

/** The version that opens without a version address: the latest version that is not discarded. */
export function findDefaultVersionNumber(versions: readonly VersionFlags[]): number | undefined {
  return (versions.findLast((version) => !version.discarded) ?? versions.at(-1))?.version_number;
}
