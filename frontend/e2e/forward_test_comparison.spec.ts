// A forward test compared with a backtest of the same period (docs/architecture/forward_test.md section 12.10) on a
// workbench: one key metric row for each test, both equity and drawdown curves, and the fill comparison in a panel.
// backend/tests/e2e_server.py adds the stopped forward test "E2E compared forward test" on FTCMP / ARCA with a start
// balance, 40 fills, equity points, 1 interruption, and the saved daily bars of its period. The forward test never runs:
// the child start function of the e2e server is a fake. The backtest runs in a real child process.
import { expect, test, type Locator, type Page } from '@playwright/test';

// A real child process runs each backtest. The browser projects share one queue.
const BACKTEST_TIMEOUT_MILLISECONDS = 90_000;
const COMPARED_STRATEGY_LABEL = 'E2E compared forward test v1';
const KEY_METRIC_NAMES = ['Total return', 'Net profit (USD)', 'Max drawdown', 'Win rate', 'Trades', 'Final equity (USD)'];

/** Opens the forward test of the list row. Returns its ID. /forward-tests first opens the newest forward test. */
async function openForwardTest(page: Page, row: Locator): Promise<string> {
  const link = row.getByRole('link', { name: /^#\d+$/ });
  const forwardTestId = ((await link.textContent()) ?? '').trim().replace('#', '');
  await link.click();
  await expect(page).toHaveURL(new RegExp(`/forward-tests/${forwardTestId}$`));
  return forwardTestId;
}

/** Checks the key metric rows of the forward test and of the backtest of the same period. */
async function expectComparedMetrics(metrics: Locator, forwardTestId: string): Promise<void> {
  // One key metric row for each test, with the metrics of the forward test page in the same order.
  const forwardTestLink = metrics.getByRole('link', { name: new RegExp(`^Forward test #${forwardTestId} ${COMPARED_STRATEGY_LABEL}$`) });
  await expect(forwardTestLink).toHaveAttribute('href', `/forward-tests/${forwardTestId}`);
  const backtestLink = metrics.getByRole('link', { name: /^Backtest #\d+$/ });
  await expect(backtestLink).toBeVisible();
  const forwardTestMetrics = metrics.locator('dl').first();
  const backtestMetrics = metrics.locator('dl').last();
  await expect(forwardTestMetrics.getByRole('term')).toHaveText(KEY_METRIC_NAMES);
  await expect(backtestMetrics.getByRole('term')).toHaveText(KEY_METRIC_NAMES);
  // The forward test records 40 fills. The bar count strategy of the backtest buys and sells 3 times.
  await expect(forwardTestMetrics.getByRole('definition').nth(4)).toHaveText('40');
  await expect(backtestMetrics.getByRole('definition').nth(4)).toHaveText('3');
  await expect(backtestMetrics.getByRole('definition').nth(2)).toHaveText(/^\s*(-[\d,]+\.\d{2}|0\.00) %$/);
  // The win rates come from the fills and the trades: a percent, not a dash.
  await expect(backtestMetrics.getByRole('definition').nth(3)).toHaveText(/^\s*\d+\.\d %$/);
}

test('backtests the same period and compares the metrics, the equity curves, and the fills', async ({ page }) => {
  test.setTimeout(BACKTEST_TIMEOUT_MILLISECONDS * 2);
  await page.setViewportSize({ width: 1280, height: 640 });
  await page.goto('/forward-tests');

  const row = page.getByRole('region', { name: 'Forward test list' }).getByRole('row', { name: /FTCMP/ });
  const forwardTestId = await openForwardTest(page, row);
  const forwardTestUrl = page.url();
  const chartPanel = page.getByRole('region', { name: `Forward test #${forwardTestId}` });
  await chartPanel.getByRole('button', { name: 'Backtest the same period', exact: true }).click();

  await expect(page).toHaveURL(/\/forward-tests\/\d+\/comparison\/\d+$/);
  await expect(page.getByRole('status', { name: 'Backtest status' })).toContainText('Finished', {
    timeout: BACKTEST_TIMEOUT_MILLISECONDS,
  });

  const metrics = page.getByRole('region', { name: 'Compared metrics' });
  await expectComparedMetrics(metrics, forwardTestId);
  await expect(page.getByRole('img', { name: 'Equity and drawdown' })).toBeVisible();
  await expect(page.getByRole('list', { name: 'Equity and drawdown legend' }).getByRole('listitem')).toHaveCount(2);
  await expect(page.getByRole('list', { name: 'Equity and drawdown interruptions' }).getByRole('listitem')).toHaveText([
    'Interrupted from 2026-03-21 01:00:00 UTC to 2026-03-24 01:00:00 UTC',
  ]);

  const tables = page.getByRole('region', { name: 'Comparison tables' });
  const fills = tables.getByRole('region', { name: 'Compared fills' });
  const firstFill = fills.getByRole('row', { name: /2026-03-03 00:00:00 UTC/ });
  await expect(firstFill).toContainText('BUY');
  await expect(firstFill).toContainText('101.01');

  const track = page.getByRole('scrollbar', { name: 'Compared fills scroll bar' });
  const lastRow = fills.getByRole('row').last();
  await fills.scrollIntoViewIfNeeded();
  await expect(track).toBeVisible();
  await expect(track.locator('.scroll-thumb')).toBeVisible();
  await expect(lastRow).not.toBeInViewport();

  await track.focus();
  await page.keyboard.press('End');

  await expect(lastRow).toBeInViewport();
  await expect(track).toHaveAttribute('aria-valuenow', '100');

  // The tables panel maximizes and restores like the panels of the other pages.
  await tables.getByRole('button', { name: 'Maximize panel' }).click();
  await expect(metrics).toBeHidden();
  await page.keyboard.press('Escape');
  await expect(metrics).toBeVisible();

  // The forward test page links to the comparison with this backtest in its Comparison tab.
  const comparisonUrl = page.url();
  const backtestId = comparisonUrl.split('/').at(-1) ?? '';
  await page.goto(forwardTestUrl);
  const forwardTestTables = page.getByRole('region', { name: 'Forward test tables' });
  await forwardTestTables.getByRole('tab', { name: 'Comparison' }).click();
  await forwardTestTables.getByRole('link', { name: `Compare with backtest #${backtestId}`, exact: true }).click();
  await expect(page).toHaveURL(comparisonUrl);
});

test('a stopped forward test shows the key metrics, the equity and drawdown chart, the fills, and the logs', async ({ page }) => {
  await page.goto('/forward-tests');
  const row = page.getByRole('region', { name: 'Forward test list' }).getByRole('row', { name: /FTCMP/ });
  const forwardTestId = await openForwardTest(page, row);

  const chartPanel = page.getByRole('region', { name: `Forward test #${forwardTestId}` });
  const heading = chartPanel.getByRole('heading', { level: 1 });
  await expect(heading.getByRole('link', { name: COMPARED_STRATEGY_LABEL })).toBeVisible();
  await expect(heading.getByRole('link', { name: 'FTCMP', exact: true })).toHaveAttribute('href', '/instruments/ARCA/FTCMP?currency=USD');
  await expect(heading).toContainText('1 day');
  await expect(chartPanel.getByRole('status', { name: 'Forward test status' })).toHaveText('Stopped');
  // A stopped forward test has no Stop button.
  await expect(chartPanel.getByRole('button', { name: 'Stop forward test' })).toHaveCount(0);
  // The same key metrics as the backtest page, in the same order. The max drawdown is a negative percent (or 0.00 %).
  await expect(chartPanel.getByRole('term')).toHaveText(KEY_METRIC_NAMES);
  await expect(chartPanel.getByRole('definition').nth(2)).toHaveText(/^\s*(-[\d,]+\.\d{2}|0\.00) %$/);
  await expect(chartPanel.getByRole('definition').nth(4)).toHaveText('40');
  await expect(chartPanel.getByRole('img', { name: 'Equity and drawdown' }).locator('canvas').first()).toBeVisible();
  await expect(chartPanel.getByRole('link', { name: 'TradingView', exact: true })).toBeVisible();
  await expect(chartPanel.getByRole('list', { name: 'Equity and drawdown interruptions' }).getByRole('listitem')).toHaveText([
    'Interrupted from 2026-03-21 01:00:00 UTC to 2026-03-24 01:00:00 UTC',
  ]);

  // The 40 fills scroll in their own region with a visible track.
  const tables = page.getByRole('region', { name: 'Forward test tables' });
  const fills = tables.getByRole('region', { name: 'Fills' });
  const track = tables.getByRole('scrollbar', { name: 'Fills scroll bar' });
  const lastFill = fills.getByRole('row').last();
  await expect(track).toBeVisible();
  await expect(lastFill).not.toBeInViewport();
  await track.focus();
  await page.keyboard.press('End');
  await expect(lastFill).toBeInViewport();

  await tables.getByRole('tab', { name: 'Logs' }).click();
  const events = tables.getByRole('region', { name: 'Logs' }).getByRole('row');
  await expect(events).toHaveText([
    /Time\s*Event/,
    /2026-03-02 00:00:00 UTC\s*Started/,
    /2026-03-21 01:00:00 UTC\s*Interrupted: Crash/,
    /2026-03-24 01:00:00 UTC\s*Continued/,
    /2026-04-16 00:00:00 UTC\s*Stopped/,
  ]);
});
