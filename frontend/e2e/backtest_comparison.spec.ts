// Backtest comparison: the backtest list refuses a selection of different strategies in its batch action bar, and
// compares two versions of the same strategy on a workbench (one key metric row for each backtest, both equity and
// drawdown curves on one chart, the code difference in the panel under it). The list scrolls inside its own region
// with a visible track.
import { expect, test, type APIRequestContext, type Locator, type Page } from '@playwright/test';

// A real child process runs each backtest. The browser projects share one queue with concurrency 1.
const BACKTEST_TIMEOUT_MILLISECONDS = 90_000;
// Backtests of a few days run fast. They fill the list, so that it overflows its region. The start route refuses a
// backtest without saved bars, so the filler backtests use the saved AAPL bars too.
const FILLER_BACKTEST_COUNT = 6;
const FULL_RANGE = { startUtc: '2023-01-02T00:00:00Z', endUtc: '2026-01-01T00:00:00Z' };
const FILLER_RANGE = { startUtc: '2023-01-02T00:00:00Z', endUtc: '2023-01-06T00:00:00Z' };
const CHANGED_CODE_LINE = '# Compared version: one more comment line.';
// More changed lines than the code difference region shows, so that it scrolls with a visible track.
const ADDED_COMMENT_LINES = Array.from({ length: 40 }, (_, index) => `# Added line ${String(index + 1)}.`).join('\n');
// The key metrics of the backtest page, in the same order.
const KEY_METRIC_NAMES = [
  'Total return',
  'Net profit (USD)',
  'Max drawdown',
  'Sharpe ratio',
  'Win rate',
  'Trades',
  'Final equity (USD)',
];

interface StrategyVersion {
  id: number;
  code: string;
}

async function createStrategy(request: APIRequestContext, name: string): Promise<{ id: number; version: StrategyVersion }> {
  // eslint-disable-next-line @typescript-eslint/naming-convention -- `data` is the request body option of Playwright.
  const strategy = (await (await request.post('/api/strategies', { data: { name } })).json()) as { id: number };
  const version = (await (await request.get(`/api/strategies/${String(strategy.id)}/versions/1`)).json()) as StrategyVersion;
  return { id: strategy.id, version };
}

async function startBacktest(
  request: APIRequestContext,
  strategyVersionId: number,
  timeRange: { startUtc: string; endUtc: string } = FULL_RANGE,
): Promise<number> {
  const response = await request.post('/api/backtests', {
    // eslint-disable-next-line @typescript-eslint/naming-convention -- `data` is the request body option of Playwright.
    data: {
      strategy_version_id: strategyVersionId,
      symbol: 'AAPL',
      exchange: 'NASDAQ',
      currency: 'USD',
      bar_period: '1-DAY',
      start_utc: timeRange.startUtc,
      end_utc: timeRange.endUtc,
      paper_capital_usd: '10000',
    },
  });
  expect(response.status()).toBe(201);
  return ((await response.json()) as { id: number }).id;
}

async function waitUntilFinished(request: APIRequestContext, backtestId: number): Promise<void> {
  await expect
    .poll(
      async () => ((await (await request.get(`/api/backtests/${String(backtestId)}`)).json()) as { status: string }).status,
      { timeout: BACKTEST_TIMEOUT_MILLISECONDS },
    )
    .toBe('finished');
}

/** In the lowest chart panel (the splitter at its maximum), the compared metrics scroll in their own region with a
 * visible track, so the last metric row stays reachable. */
async function expectMetricsReachableInLowPanel(page: Page): Promise<void> {
  const splitter = page.getByRole('separator', { name: 'Resize the chart and the tables' });
  await splitter.focus();
  await page.keyboard.press('End');
  await expect(splitter).toHaveAttribute('aria-valuenow', (await splitter.getAttribute('aria-valuemax')) ?? '');
  const metricsTrack = page.getByRole('scrollbar', { name: 'Compared metrics scroll bar' });
  const lastMetricRow = page.getByRole('region', { name: 'Compared metrics' }).locator('dl').last();
  await expect(metricsTrack).toBeVisible();
  await expect(lastMetricRow).not.toBeInViewport({ ratio: 1 });
  await metricsTrack.focus();
  await page.keyboard.press('End');
  await expect(lastMetricRow).toBeInViewport({ ratio: 1 });
}

/** Checks the comparison workbench of 2 backtests with these names: the key metric rows, the chart, the code
 * difference, and the panel controls. */
async function expectComparisonWorkbench(page: Page, chartPanel: Locator, labels: string[]): Promise<void> {
  const [firstLabel = '', secondLabel = ''] = labels;
  // One key metric row for each backtest: the same metrics in the same order as on the backtest page.
  const metrics = chartPanel.getByRole('region', { name: 'Compared metrics' });
  await expect(metrics.getByRole('link', { name: firstLabel })).toBeVisible();
  await expect(metrics.getByRole('link', { name: secondLabel })).toBeVisible();
  for (const label of [firstLabel, secondLabel]) {
    const row = metrics.locator(`dl[aria-label="Metrics of ${label}"]`);
    await expect(row.getByRole('term')).toHaveText(KEY_METRIC_NAMES);
    await expect(row.getByRole('definition').nth(2)).toHaveText(/^\s*(-[\d,]+\.\d{2}|0\.00) %$/);
  }
  await expect(chartPanel.getByRole('img', { name: 'Equity and drawdown' }).locator('canvas').first()).toBeVisible();
  // The name lines with the curve line styles name the curves: the chart has no second legend.
  await expect(chartPanel.getByRole('list', { name: 'Equity and drawdown legend' })).toHaveCount(0);

  const tables = page.getByRole('region', { name: 'Comparison tables' });
  await expect(tables.getByRole('tab', { name: 'Code difference' })).toHaveAttribute('aria-selected', 'true');
  await expect(tables.locator('.cm-mergeView')).toContainText(CHANGED_CODE_LINE);
  // Only the changed lines and a few lines around them show. The unchanged lines are collapsed.
  await expect(tables.locator('.cm-collapsedLines').first()).toBeVisible();
  await expect(tables.locator('.cm-mergeView')).not.toContainText('class MovingAverageStrategy(Strategy):');
  const diffTrack = tables.getByRole('scrollbar', { name: 'Code difference scroll bar' });
  await expect(diffTrack).toBeVisible();
  await expect(diffTrack.locator('.scroll-thumb')).toBeVisible();

  // The code difference panel maximizes and restores like the panels of the other pages.
  await tables.getByRole('button', { name: 'Maximize panel' }).click();
  await expect(metrics).toBeHidden();
  await page.keyboard.press('Escape');
  await expect(metrics).toBeVisible();
  await chartPanel.getByRole('button', { name: 'Minimize panel' }).click();
  await expect(metrics).toBeHidden();
  await chartPanel.getByRole('button', { name: 'Restore panel' }).click();
  await expect(metrics).toBeVisible();
  await expectMetricsReachableInLowPanel(page);
}

test('compares two versions of the same strategy and refuses different strategies', async ({ page, request }, currentTest) => {
  test.setTimeout(BACKTEST_TIMEOUT_MILLISECONDS * 2);
  // A low window, so that the backtest list overflows its region.
  await page.setViewportSize({ width: 1280, height: 400 });
  // The chart saves the daily bars from 2023-01-02 to 2026-01-01 in PostgreSQL. Backtests read only saved bars.
  await page.goto('/instruments/NASDAQ/AAPL?currency=USD&bar_period=1-DAY');
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('1096 bars');

  // The e2e database is not cleared between tests and browser projects, so the strategy names are unique.
  const suffix = `${currentTest.project.name} ${String(Date.now())}`;
  const compared = await createStrategy(request, `Compared ${suffix}`);
  const other = await createStrategy(request, `Other ${suffix}`);
  const secondVersionResponse = await request.post(`/api/strategies/${String(compared.id)}/versions`, {
    // eslint-disable-next-line @typescript-eslint/naming-convention -- `data` is the request body option of Playwright.
    data: { code: `${compared.version.code}\n${CHANGED_CODE_LINE}\n${ADDED_COMMENT_LINES}\n` },
  });
  const secondVersion = (await secondVersionResponse.json()) as StrategyVersion;
  const firstBacktestId = await startBacktest(request, compared.version.id);
  const secondBacktestId = await startBacktest(request, secondVersion.id);
  const otherBacktestId = await startBacktest(request, other.version.id);
  for (let fillerIndex = 0; fillerIndex < FILLER_BACKTEST_COUNT; fillerIndex += 1) {
    await startBacktest(request, other.version.id, FILLER_RANGE);
  }
  await waitUntilFinished(request, firstBacktestId);
  await waitUntilFinished(request, secondBacktestId);

  await page.goto(`/backtests/${String(firstBacktestId)}`);
  const list = page.getByRole('complementary', { name: 'Backtests' });
  const track = page.getByRole('scrollbar', { name: 'Backtest list scroll bar' });
  await expect(list.getByRole('columnheader', { name: 'Return' })).toBeVisible();
  await expect(track).toBeVisible();
  await expect(track.locator('.scroll-thumb')).toBeVisible();

  // The Carbon batch action bar shows when 2 rows are checked.
  const selection = list.getByRole('status', { name: 'Comparison selection' });
  await list.getByRole('checkbox', { name: `Select backtest #${String(firstBacktestId)}`, exact: true }).check();
  await expect(selection).toHaveCount(0);
  await list.getByRole('checkbox', { name: `Select backtest #${String(otherBacktestId)}`, exact: true }).check();
  await expect(selection).toHaveText('Only backtests of the same strategy can be compared');
  await expect(list.getByRole('button', { name: 'Compare', exact: true })).toBeDisabled();

  await list.getByRole('checkbox', { name: `Select backtest #${String(otherBacktestId)}`, exact: true }).uncheck();
  await list.getByRole('checkbox', { name: `Select backtest #${String(secondBacktestId)}`, exact: true }).check();
  await expect(selection).toHaveText('2 backtests selected');
  // A window of normal height for the comparison workbench.
  await page.setViewportSize({ width: 1280, height: 800 });
  await list.getByRole('link', { name: 'Compare', exact: true }).click();

  const title = `Compare backtests #${String(firstBacktestId)} and #${String(secondBacktestId)}`;
  const chartPanel = page.getByRole('region', { name: title, exact: true });
  await expect(chartPanel.getByRole('heading', { level: 1 })).toHaveText(
    new RegExp(`^\\s*${title}\\s*Compared ${suffix}\\s*AAPL\\s*1 day\\s*$`),
  );
  // Both compared rows of the side column have the open row color.
  await expect(list.getByRole('row', { name: new RegExp(`#${String(firstBacktestId)} `) })).toHaveClass(/cds--data-table--selected/);
  await expect(list.getByRole('row', { name: new RegExp(`#${String(secondBacktestId)} `) })).toHaveClass(/cds--data-table--selected/);

  await expectComparisonWorkbench(page, chartPanel, [
    `#${String(firstBacktestId)} Compared ${suffix} v1`,
    `#${String(secondBacktestId)} Compared ${suffix} v2`,
  ]);
  await expect(chartPanel.getByRole('region', { name: 'Compared metrics' }).getByRole('link').first()).toHaveAttribute(
    'href',
    `/backtests/${String(firstBacktestId)}`,
  );

  // The backend also refuses a comparison of different strategies, for example from a typed URL.
  await page.goto(`/backtests/${String(firstBacktestId)}/comparison/${String(otherBacktestId)}`);
  await expect(page.getByRole('alert')).toHaveText(/Only backtests of the same strategy can be compared/);
});

test('shows a note instead of an empty code difference for the same strategy version', async ({ page, request }, currentTest) => {
  // The chart saves the daily bars in PostgreSQL. The start route refuses a backtest without saved bars.
  await page.goto('/instruments/NASDAQ/AAPL?currency=USD&bar_period=1-DAY');
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('1096 bars');
  const compared = await createStrategy(request, `Same version ${currentTest.project.name} ${String(Date.now())}`);
  const firstBacktestId = await startBacktest(request, compared.version.id, FILLER_RANGE);
  const secondBacktestId = await startBacktest(request, compared.version.id, FILLER_RANGE);

  await page.goto(`/backtests/${String(firstBacktestId)}/comparison/${String(secondBacktestId)}`);

  await expect(page.getByText('No code difference', { exact: true })).toBeVisible();
  await expect(page.locator('.cm-mergeView')).toHaveCount(0);
  await page.getByText('Show the code').click();
  // The full code shows: no collapsed lines. CodeMirror draws only the lines near the visible part.
  await expect(page.locator('.cm-mergeView')).toContainText('from nautilus_trader.trading import Strategy');
  await expect(page.locator('.cm-collapsedLines')).toHaveCount(0);
  // The code scrolls inside its region, and CodeMirror draws the lines that the scroll shows.
  await page.getByRole('region', { name: 'Code difference' }).evaluate((region) => {
    region.scrollTop = region.scrollHeight;
  });
  await expect(page.locator('.cm-mergeView')).toContainText('self.submit_order(order)');
});
