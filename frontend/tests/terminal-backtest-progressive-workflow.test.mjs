import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';

const root = path.resolve(import.meta.dirname, '..');
const workspacePath = path.join(root, 'components', 'terminal', 'TerminalBacktestWorkspace.tsx');
const workflowPath = path.join(root, 'lib', 'terminalBacktestWorkflow.ts');
const comparisonPath = path.join(root, 'components', 'terminal', 'BacktestComparisonPanel.tsx');
const cssPath = path.join(root, 'app', 'globals.css');

const progressiveSections = [
  'backtest-step-capital',
  'backtest-step-instrument',
  'backtest-step-strategy',
  'backtest-step-advanced',
  'backtest-step-create',
  'backtest-step-live-status',
  'backtest-step-history',
  'backtest-step-detail',
  'backtest-step-comparison',
];

test('backtest workspace is a progressive saved-run workflow in the intended task order', async () => {
  const workspace = await readFile(workspacePath, 'utf8');

  assertInOrder(workspace, [
    '<BacktestCapitalPanel workflow={workflow} />',
    '<BacktestRunForm workflow={workflow} />',
    '<BacktestLiveStatusPanel workflow={workflow} />',
    '<BacktestHistoryPanel workflow={workflow} />',
    '<BacktestRunDetailPanel workflow={workflow} />',
    'data-testid="backtest-step-comparison"',
  ]);
  assertInOrder(workspace, progressiveSections.slice(0, 5).map((testId) => `data-testid="${testId}"`));
  for (const testId of progressiveSections) {
    assert.match(workspace, new RegExp(`data-testid="${testId}"`), `missing progressive section ${testId}`);
  }
  assert.match(workspace, /Effective capital/i);
  assert.match(workspace, /Selected instrument/i);
  assert.match(workspace, /Strategy setup/i);
  assert.match(workspace, /Advanced settings/i);
  assert.match(workspace, /Create saved run/i);
  assert.match(workspace, /Live selected-run status/i);
  assert.match(workspace, /Saved history/i);
  assert.match(workspace, /Saved run detail/i);
  assert.match(workspace, /Completed-run comparison/i);

  assertInOrder(workspace, [
    '<BacktestRunDetailPanel workflow={workflow} />',
    '<BacktestComparisonPanel workflow={workflow} />',
  ]);
});

test('required inputs and advanced settings are visibly grouped without hiding saved-run context', async () => {
  const workspace = await readFile(workspacePath, 'utf8');

  assert.match(workspace, /data-testid="backtest-required-inputs"/);
  assert.match(workspace, /data-testid="backtest-strategy-setup"/);
  assert.match(workspace, /data-testid="backtest-advanced-settings"/);
  assert.match(workspace, /Required inputs/i);
  assert.match(workspace, /Cost, slippage, and benchmark/i);
  assert.match(workspace, /Single stock symbol/);
  assert.match(workspace, /Chart range/);
  assert.match(workspace, /Strategy/);
  assert.match(workspace, /Commission \/ trade/);
  assert.match(workspace, /Slippage bps/);
  assert.match(workspace, /Benchmark/);
});

test('run status, history, detail, comparison, cancel, retry, fallback, and scroll affordances stay truthful', async () => {
  const [workspace, workflow, comparison, css] = await Promise.all([
    readFile(workspacePath, 'utf8'),
    readFile(workflowPath, 'utf8'),
    readFile(comparisonPath, 'utf8'),
    readFile(cssPath, 'utf8'),
  ]);

  for (const status of ['queued', 'running', 'completed', 'failed', 'cancelled']) {
    assert.match(workspace + workflow, new RegExp(`'${status}'`), `missing truthful status handling for ${status}`);
  }

  assert.match(workspace, /data-testid="backtest-cancel-run-button"/);
  assert.match(workspace, /data-testid="backtest-retry-run-button"/);
  assert.match(workflow, /connectBacktestRunStream\(\{/);
  assert.match(workflow, /state === 'connected' && reconnectingRef\.current/);
  assert.match(workflow, /void loadHistory\(\)/);
  assert.match(workflow, /void loadRunDetail\(selectedRunIdRef\.current\)/);
  assert.doesNotMatch(workflow, /workspaceStatus|globalSignalR|GlobalSignalR|setGlobal/i);

  assert.match(workspace, /data-scroll-owner="backtest-module"/);
  assert.match(workspace, /data-scroll-owner="backtest-history"/);
  assert.match(workspace, /data-scroll-owner="backtest-signals-list"/);
  assert.match(workspace, /data-scroll-owner="backtest-trades-list"/);
  assert.match(comparison, /data-scroll-owner="backtest-comparison"/);
  assert.match(comparison, /data-scroll-owner="backtest-comparison-metrics"/);
  assertCssRuleContains(css, '.terminal-backtest-history__list', ['overflow: auto']);
  assertCssRuleContains(css, '.terminal-backtest-detail__scroll-list', ['overflow: auto']);

  assert.match(workflow, /isBacktestStatus\(run\.status, 'completed'\)/);
  assert.match(workflow, /normalizeBacktestEquitySeries\(run\.result\.equityCurve/);
  assert.match(workspace + comparison, /No demo runs|no synthetic benchmark|no fake result|synthetic equity curves/i);
});

test('backtest workflow does not introduce out-of-scope controls', async () => {
  const source = await Promise.all([workspacePath, workflowPath, comparisonPath].map((file) => readFile(file, 'utf8'))).then((parts) => parts.join('\n'));

  assert.doesNotMatch(source, /Place order|Submit order|Preview order|Confirm order|OrderTicket|MarketOrder|LimitOrder|buy-button|sell-button/i);
  assert.doesNotMatch(source, /Export comparison|Download CSV|Optimization|Optimize|Custom code|Live trading|SetLiveMode/i);
  assert.doesNotMatch(source, /type="submit"/i);
});

function assertInOrder(source, needles) {
  let cursor = -1;
  for (const needle of needles) {
    const index = source.indexOf(needle, cursor + 1);
    assert.ok(index > cursor, `Expected to find ${needle} after offset ${cursor}`);
    cursor = index;
  }
}

function assertCssRuleContains(css, selector, declarations) {
  const escapedSelector = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const matches = [...css.matchAll(new RegExp(`${escapedSelector}\\s*\\{(?<body>[^}]*)\\}`, 'gm'))];
  assert.ok(matches.length > 0, `Expected CSS rule for ${selector}`);

  const normalizedBodies = matches.map((match) => match.groups.body.replace(/\s+/g, ' ').trim());
  for (const declaration of declarations) {
    assert.ok(
      normalizedBodies.some((body) => body.includes(declaration)),
      `Expected ${selector} to include "${declaration}". Rules were: ${normalizedBodies.join(' || ')}`,
    );
  }
}
