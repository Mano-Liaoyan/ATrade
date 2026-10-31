// The strategy workbench state: the pane order, the result tabs, the finished backtest that opens, and the shortcuts.
import { languageServerExtensions } from '@codemirror/lsp-client';
import { EditorState, type Extension } from '@codemirror/state';
import { keymap } from '@codemirror/view';
import { basicSetup } from 'codemirror';
import { describe, expect, it } from 'vite-plus/test';
import type { Backtest } from '#lib/backtest';
import type { ForwardTest } from '#lib/forward_test';
import {
  EDITOR_SHORTCUT_KEYS,
  closeBacktestTab,
  createOutputLine,
  describeBacktestEvent,
  describeFixRequest,
  describeProblemCounts,
  describeShortcut,
  describeSwapButton,
  findClosedBacktestIds,
  findFinishedBacktest,
  findDefaultVersionNumber,
  findRunningForwardTest,
  listResultTabs,
  listVersionItems,
  listWorkbenchPanels,
  readClosedBacktestTabs,
  readPaneOrder,
  readWorkbenchShortcut,
  resolveResultTab,
  swapPaneOrder,
} from './strategy_workbench';

function createBacktest(id: number, strategyId: number, status: Backtest['status'], totalReturn?: string): Backtest {
  return {
    id,
    strategy_id: strategyId,
    status,
    error_message: null,
    metrics:
      totalReturn === undefined
        ? null
        : { total_return_percent: totalReturn, net_profit_usd: '0', max_drawdown_percent: '0', final_equity_usd: '0', trade_count: 0 },
  } as Backtest;
}

describe('readPaneOrder', () => {
  it('puts the results on top by default and for a damaged value', () => {
    expect(readPaneOrder(null)).toBe('results-on-top');
    expect(readPaneOrder('sideways')).toBe('results-on-top');
    expect(readPaneOrder('editor-on-top')).toBe('editor-on-top');
  });
});

describe('swapPaneOrder and listWorkbenchPanels', () => {
  it('lists the results over the editor, and the swap puts the editor on top', () => {
    expect(listWorkbenchPanels('results-on-top').map((panel) => panel.id)).toEqual(['results', 'editor', 'output']);
    expect(swapPaneOrder('results-on-top')).toBe('editor-on-top');
    expect(listWorkbenchPanels('editor-on-top').map((panel) => panel.id)).toEqual(['editor', 'results', 'output']);
    expect(swapPaneOrder('editor-on-top')).toBe('results-on-top');
  });

  it('gives both panels a height, so each one can be the lower panel', () => {
    for (const panel of listWorkbenchPanels('results-on-top').slice(0, 2)) {
      expect(panel.defaultPixels).toBeGreaterThan(0);
      expect(panel.splitterLabel).toBe('Resize the results and the editor');
    }
  });

  it('puts the problems and output panel at the bottom, minimized to its status bar by default', () => {
    expect(listWorkbenchPanels('editor-on-top').at(-1)).toEqual({
      id: 'output',
      minPixels: 96,
      defaultPixels: 240,
      splitterLabel: 'Resize the problems and output',
      startsMinimized: true,
    });
  });
});

describe('describeProblemCounts', () => {
  it('counts all code problems as errors, because the checks give no severity', () => {
    const problems = [
      { line: 1, message: 'F821 Undefined name `a`' },
      { line: 4, message: 'F821 Undefined name `b`' },
    ];

    expect(describeProblemCounts(problems)).toEqual({ errors: 2, warnings: 0, label: 'Problems: 2 errors, 0 warnings' });
    expect(describeProblemCounts([]).label).toBe('Problems: 0 errors, 0 warnings');
  });
});

describe('createOutputLine', () => {
  it('starts the line with the UTC time', () => {
    expect(createOutputLine(new Date('2026-10-28T05:04:03.250Z'), 'Saved as Trend v2.')).toBe('05:04:03  Saved as Trend v2.');
  });
});

describe('describeBacktestEvent', () => {
  it('names the backtest and its status', () => {
    expect(describeBacktestEvent(createBacktest(14, 3, 'queued'))).toBe('Backtest #14 queued.');
    expect(describeBacktestEvent(createBacktest(14, 3, 'finished', '1'))).toBe('Backtest #14 finished.');
    expect(describeBacktestEvent(createBacktest(14, 3, 'timed_out'))).toBe('Backtest #14 timed out.');
    expect(describeBacktestEvent({ ...createBacktest(14, 3, 'failed'), error_message: 'No bars' })).toBe(
      'Backtest #14 failed: No bars',
    );
  });
});

describe('describeSwapButton', () => {
  it('points the arrow to the place that the editor moves to', () => {
    expect(describeSwapButton('results-on-top')).toEqual({ label: 'Put editor on top', direction: 'up' });
    expect(describeSwapButton('editor-on-top')).toEqual({ label: 'Put editor at bottom', direction: 'down' });
  });
});

describe('listResultTabs', () => {
  it('has one tab for each backtest of the strategy, the newest first, and the fixed Trades, Orders, and Logs', () => {
    const backtests = [
      createBacktest(13, 3, 'finished', '-2.5'),
      createBacktest(9, 4, 'finished', '1'),
      createBacktest(14, 3, 'running'),
    ];

    expect(listResultTabs(backtests, 3)).toEqual({
      backtestTabs: [
        { value: 'backtest-14', label: 'Backtest #14', name: 'Backtest #14', backtestId: 14, status: 'running', change: null, changeText: '' },
        {
          value: 'backtest-13',
          label: 'Backtest #13 -2.50 %',
          name: 'Backtest #13',
          backtestId: 13,
          status: 'finished',
          change: -2.5,
          changeText: '-2.50 %',
        },
      ],
      tableTabs: [
        { value: 'trades', label: 'Trades', name: 'Trades', backtestId: null, status: null, change: null, changeText: '' },
        { value: 'orders', label: 'Orders', name: 'Orders', backtestId: null, status: null, change: null, changeText: '' },
        { value: 'logs', label: 'Logs', name: 'Logs', backtestId: null, status: null, change: null, changeText: '' },
      ],
    });
  });

  it('leaves out the closed backtest tabs', () => {
    const backtests = [createBacktest(14, 3, 'failed'), createBacktest(13, 3, 'finished', '1')];

    expect(listResultTabs(backtests, 3, new Set([14])).backtestTabs.map((tab) => tab.value)).toEqual(['backtest-13']);
  });
});

describe('closed backtest tabs', () => {
  it('keeps the closed backtests of each strategy', () => {
    const closed = closeBacktestTab(closeBacktestTab(readClosedBacktestTabs(null), 3, 14), 4, 9);

    expect(closed).toEqual({ '3': [14], '4': [9] });
    expect(findClosedBacktestIds(closed, 3)).toEqual(new Set([14]));
    expect(findClosedBacktestIds(closed, 5)).toEqual(new Set());
  });

  it('reads a damaged stored value as no closed tabs', () => {
    expect(readClosedBacktestTabs('x')).toEqual({});
    expect(readClosedBacktestTabs({ '3': ['a', 2] })).toEqual({ '3': [2] });
  });
});

describe('resolveResultTab', () => {
  const backtests = [createBacktest(14, 3, 'finished', '1'), createBacktest(13, 3, 'finished', '2')];

  it('opens the newest backtest when nothing is selected', () => {
    expect(resolveResultTab({ tab: null, backtestId: null }, backtests, 3)).toEqual({ tab: 'backtest-14', backtestId: 14 });
  });

  it('keeps the selected backtest for Trades, Orders, and Logs', () => {
    expect(resolveResultTab({ tab: 'trades', backtestId: 13 }, backtests, 3)).toEqual({ tab: 'trades', backtestId: 13 });
  });

  it('falls back to the newest backtest when the selected one is not of this strategy', () => {
    expect(resolveResultTab({ tab: 'backtest-99', backtestId: 99 }, backtests, 3)).toEqual({ tab: 'backtest-14', backtestId: 14 });
  });

  it('opens the newest open tab when the selected tab is closed', () => {
    expect(resolveResultTab({ tab: 'backtest-14', backtestId: 14 }, backtests, 3, new Set([14]))).toEqual({
      tab: 'backtest-13',
      backtestId: 13,
    });
  });

  it('opens Trades with no backtest when the strategy has no backtest', () => {
    expect(resolveResultTab({ tab: null, backtestId: null }, [], 3)).toEqual({ tab: 'trades', backtestId: null });
  });
});

describe('describeFixRequest', () => {
  it('asks the AI assistant to read the failed backtest and fix the code', () => {
    expect(describeFixRequest(21)).toBe('Backtest #21 failed. Read it with read_backtest and fix the strategy code.');
  });
});

describe('findFinishedBacktest', () => {
  it('finds a backtest of the strategy that was running and is now final', () => {
    const previous = [createBacktest(14, 3, 'running'), createBacktest(15, 4, 'running')];
    const next = [createBacktest(14, 3, 'failed'), createBacktest(15, 4, 'finished', '1')];

    expect(findFinishedBacktest(previous, next, 3)?.id).toBe(14);
    expect(findFinishedBacktest(next, next, 3)).toBeNull();
  });

  it('ignores a backtest that is new in the list and already final', () => {
    expect(findFinishedBacktest([], [createBacktest(14, 3, 'finished', '1')], 3)).toBeNull();
  });
});

// A CodeMirror key name in one form for a platform: Mod as Meta on macOS and as Ctrl elsewhere, Cmd as Meta, the
// modifiers in a fixed order, lower case.
function normalizeKey(key: string, isMac: boolean): string {
  const parts = key.toLowerCase().split('-');
  const name = parts.pop() ?? '';
  const aliases: Record<string, string> = { mod: isMac ? 'meta' : 'ctrl', cmd: 'meta', c: 'ctrl', m: 'meta', s: 'shift', a: 'alt' };
  const modifiers = parts.map((part) => aliases[part] ?? part);
  return [...new Set(modifiers)].sort().concat(name).join('-');
}

// The keys of the code editor and its language server client on a platform.
function listEditorKeys(isMac: boolean): string[] {
  // The client gives its editor parts in `editorExtension` (LSPClientExtension), or as plain extensions.
  const clientExtensions = languageServerExtensions().map((extension): Extension => {
    const editorExtension: unknown = Reflect.get(extension, 'editorExtension');
    return (editorExtension ?? extension) as Extension;
  });
  const state = EditorState.create({ extensions: [basicSetup, clientExtensions] });
  return state
    .facet(keymap)
    .flat()
    .map((binding) => (isMac ? (binding.mac ?? binding.key) : (binding.win ?? binding.linux ?? binding.key)))
    .filter((key) => key !== undefined)
    .map((key) => normalizeKey(key, isMac));
}

describe('findRunningForwardTest', () => {
  function createForwardTest(id: number, strategyId: number, desiredState: ForwardTest['desired_state']): ForwardTest {
    return { id, strategy_id: strategyId, desired_state: desiredState } as ForwardTest;
  }

  it('finds the newest running forward test of the strategy', () => {
    const forwardTests = [
      createForwardTest(5, 3, 'running'),
      createForwardTest(8, 3, 'running'),
      createForwardTest(9, 4, 'running'),
      createForwardTest(10, 3, 'stopped'),
    ];

    expect(findRunningForwardTest(forwardTests, 3)?.id).toBe(8);
    expect(findRunningForwardTest([createForwardTest(10, 3, 'stopped')], 3)).toBeNull();
  });
});

describe('readWorkbenchShortcut', () => {
  const noKeys = { ctrlKey: false, metaKey: false, shiftKey: false, altKey: false };

  it('reads Ctrl S, Ctrl B, and Ctrl Shift F', () => {
    expect(readWorkbenchShortcut({ ...noKeys, key: 's', ctrlKey: true }, false)).toBe('save');
    expect(readWorkbenchShortcut({ ...noKeys, key: 'b', ctrlKey: true }, false)).toBe('backtest');
    expect(readWorkbenchShortcut({ ...noKeys, key: 'F', ctrlKey: true, shiftKey: true }, false)).toBe('forward-test');
  });

  it('reads Cmd on macOS, where Ctrl B moves the cursor in the editor', () => {
    expect(readWorkbenchShortcut({ ...noKeys, key: 'b', metaKey: true }, true)).toBe('backtest');
    expect(readWorkbenchShortcut({ ...noKeys, key: 'b', ctrlKey: true }, true)).toBeNull();
    expect(readWorkbenchShortcut({ ...noKeys, key: 's', metaKey: true }, false)).toBeNull();
  });

  it('ignores other keys and the keys without Ctrl', () => {
    expect(readWorkbenchShortcut({ ...noKeys, key: 's' }, false)).toBeNull();
    expect(readWorkbenchShortcut({ ...noKeys, key: 'f', ctrlKey: true }, false)).toBeNull();
    expect(readWorkbenchShortcut({ ...noKeys, key: 'b', ctrlKey: true, altKey: true }, false)).toBeNull();
    expect(readWorkbenchShortcut({ ...noKeys, key: 'S', ctrlKey: true, shiftKey: true }, false)).toBeNull();
  });

  it('uses no key of the code editor and its language server client', () => {
    for (const isMac of [false, true]) {
      const editorKeys = listEditorKeys(isMac);
      expect(editorKeys).toContain(normalizeKey('Mod-f', isMac));
      for (const key of Object.values(EDITOR_SHORTCUT_KEYS)) {
        expect(editorKeys).not.toContain(normalizeKey(key, isMac));
      }
    }
  });

  it('names the shortcut keys of the platform in the tooltip', () => {
    expect(describeShortcut('forward-test', false)).toBe('Ctrl+Shift+F');
    expect(describeShortcut('save', true)).toBe('Cmd+S');
  });
});

describe('listVersionItems', () => {
  const versions = [
    { version_number: 1, discarded: false },
    { version_number: 2, discarded: true },
    { version_number: 3, discarded: false },
  ];

  it('hides the discarded versions by default', () => {
    expect(listVersionItems(versions, { showDiscarded: false, openVersionNumber: 3 })).toEqual([
      { value: '1', label: 'v1' },
      { value: '3', label: 'v3' },
    ]);
  });

  it('shows the discarded versions with the tag Discarded when the toggle is on', () => {
    expect(listVersionItems(versions, { showDiscarded: true, openVersionNumber: 3 })).toEqual([
      { value: '1', label: 'v1' },
      { value: '2', label: 'v2', tag: 'Discarded' },
      { value: '3', label: 'v3' },
    ]);
  });

  it('keeps the open version in the list when it is discarded', () => {
    expect(listVersionItems(versions, { showDiscarded: false, openVersionNumber: 2 })).toEqual([
      { value: '1', label: 'v1' },
      { value: '2', label: 'v2', tag: 'Discarded' },
      { value: '3', label: 'v3' },
    ]);
  });
});

describe('findDefaultVersionNumber', () => {
  it('opens the latest version that is not discarded', () => {
    expect(
      findDefaultVersionNumber([
        { version_number: 1, discarded: false },
        { version_number: 2, discarded: true },
      ]),
    ).toBe(1);
  });

  it('opens the latest version when all versions are discarded', () => {
    expect(findDefaultVersionNumber([{ version_number: 4, discarded: true }])).toBe(4);
    expect(findDefaultVersionNumber([])).toBeUndefined();
  });
});
