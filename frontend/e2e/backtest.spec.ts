// Backtest workbench (#104): start a backtest of the template strategy on saved bars from the New backtest dialog, and
// see the list and the result on one page that does not scroll: the key metric row, the equity and drawdown curves,
// and the Trades / Orders / Logs panel. The bar chart saves the bars first: the IBKR fake of
// backend/tests/e2e_server.py has one daily bar for each day, with saw-tooth prices. The form offers only watchlist
// instruments with saved bars of the selected bar period.
import { expect, test, type Page } from '@playwright/test';

// A real child process runs each backtest. The browser projects share one queue with concurrency 1.
const BACKTEST_TIMEOUT_MILLISECONDS = 60_000;
const KEY_METRIC_NAMES = ['Total return', 'Net profit (USD)', 'Max drawdown', 'Win rate', 'Trades', 'Final equity (USD)'];

async function expectNoPageScroll(page: Page): Promise<void> {
  const sizes = await page.evaluate(() => ({
    scrollHeight: document.documentElement.scrollHeight,
    clientHeight: document.documentElement.clientHeight,
  }));
  expect(sizes.scrollHeight).toBeLessThanOrEqual(sizes.clientHeight);
}

async function startBacktestInDialog(page: Page, strategyName: string): Promise<void> {
  await page.getByRole('button', { name: 'New backtest' }).click();
  const dialog = page.getByRole('dialog', { name: 'New backtest' });
  // The e2e server paper account balance is the default paper capital.
  await expect(dialog.getByLabel('Paper capital (USD)')).toHaveValue('101234.50');
  // The selects are Carbon dropdowns: the trigger is a combo box, and the choices are options.
  await dialog.getByRole('combobox', { name: 'Strategy', exact: true }).click();
  await page.getByRole('option', { name: strategyName, exact: true }).click();
  await expect(dialog.getByRole('combobox', { name: 'Strategy version' })).toHaveText(`${strategyName} v1`);
  await dialog.getByRole('combobox', { name: 'Bar period' }).click();
  await page.getByRole('option', { name: '1 day', exact: true }).click();
  await dialog.getByRole('combobox', { name: 'Instrument', exact: true }).click();
  await page.getByRole('option', { name: 'AAPL / NASDAQ / USD', exact: true }).click();
  await expect(dialog.getByRole('status', { name: 'Saved bars' })).toHaveText(
    'Saved bars start from 2023-01-02 00:00:00 UTC to 2026-01-01 00:00:00 UTC.',
  );
  await dialog.getByLabel('Start date (UTC)').fill('2023-01-02');
  await dialog.getByLabel('End date (UTC)').fill('2026-01-01');
  await dialog.getByRole('button', { name: 'Start backtest' }).click();
}

// The trades scroll in their own region with a visible track. The API has no orders and no logs of a finished backtest.
async function expectTradesOrdersAndLogs(page: Page): Promise<void> {
  const tables = page.getByRole('region', { name: 'Backtest tables' });
  const trades = tables.getByRole('region', { name: 'Trades' });
  const track = tables.getByRole('scrollbar', { name: 'Trades scroll bar' });
  const lastRow = trades.getByRole('row').last();
  await expect(track).toBeVisible();
  await expect(track.locator('.scroll-thumb')).toBeVisible();
  await expect(lastRow).not.toBeInViewport();
  await track.focus();
  await page.keyboard.press('End');
  await expect(lastRow).toBeInViewport();
  await expect(track).toHaveAttribute('aria-valuenow', '100');

  await tables.getByRole('tab', { name: 'Orders' }).click();
  await expect(tables).toContainText('No orders');
  await tables.getByRole('tab', { name: 'Logs' }).click();
  await expect(tables).toContainText('No logs');
}

test('starts a backtest and sees its metrics, curves, and trades on the workbench', async ({ page, request }, currentTest) => {
  test.setTimeout(BACKTEST_TIMEOUT_MILLISECONDS * 2);
  // The chart saves the daily bars from 2023-01-02 to 2026-01-01 in PostgreSQL. Backtests read only saved bars.
  await page.goto('/instruments/NASDAQ/AAPL?currency=USD&bar_period=1-DAY');
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('1096 bars');
  // The browser projects share one database: another project can add AAPL first (409).
  // eslint-disable-next-line @typescript-eslint/naming-convention -- `data` is the request body option of Playwright.
  const watchlistResponse = await request.post('/api/watchlist', { data: { symbol: 'AAPL', exchange: 'NASDAQ', currency: 'USD' } });
  expect([201, 409]).toContain(watchlistResponse.status());
  // The e2e database is not cleared between tests and browser projects, so the strategy name is unique.
  const strategyName = `Backtest ${currentTest.project.name} ${String(Date.now())}`;
  await page.goto('/strategies');
  await page.getByRole('button', { name: 'New strategy' }).click();
  await page.getByLabel('Strategy name').fill(strategyName);
  await page.getByRole('button', { name: 'Create strategy' }).click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(strategyName);

  await page.getByRole('link', { name: 'Backtests' }).click();
  await startBacktestInDialog(page, strategyName);

  await expect(page.getByRole('dialog', { name: 'New backtest' })).toHaveCount(0);
  await expect(page).toHaveURL(/\/backtests\/\d+$/);
  const backtestId = page.url().split('/').at(-1) ?? '';
  const chartPanel = page.getByRole('region', { name: `Backtest #${backtestId}` });
  const heading = chartPanel.getByRole('heading', { level: 1 });
  await expect(heading).toContainText(`#${backtestId}`);
  await expect(heading.getByRole('link', { name: `${strategyName} v1` })).toHaveAttribute('href', /^\/strategies\/\d+\/versions\/1$/);
  await expect(heading.getByRole('link', { name: 'AAPL', exact: true })).toHaveAttribute('href', '/instruments/NASDAQ/AAPL?currency=USD');
  await expect(heading).toContainText('1 day');
  await expect(chartPanel.getByRole('status', { name: 'Backtest status' })).toHaveText('Finished', {
    timeout: BACKTEST_TIMEOUT_MILLISECONDS,
  });
  // The open backtest is the current row of the list.
  const list = page.getByRole('complementary', { name: 'Backtests' });
  await expect(list.getByRole('link', { name: `#${backtestId}`, exact: true })).toHaveAttribute('aria-current', 'page');

  // One set of key metrics in one order. The max drawdown is a negative percent (or 0.00 %).
  const metrics = chartPanel.getByRole('definition');
  await expect(chartPanel.getByRole('term')).toHaveText(KEY_METRIC_NAMES);
  await expect(metrics.nth(2)).toHaveText(/^\s*(-[\d,]+\.\d{2}|0\.00) %$/);
  await expect(chartPanel.getByRole('img', { name: 'Equity and drawdown' }).locator('canvas').first()).toBeVisible();
  await expect(chartPanel.getByRole('link', { name: 'TradingView', exact: true })).toBeVisible();
  // Daily bars are live bars, so the forward test of the same version, instrument, and bar period can start.
  await expect(chartPanel.getByRole('button', { name: 'Start forward test', exact: true })).not.toHaveAttribute(
    'aria-disabled',
  );
  await expectNoPageScroll(page);

  await expectTradesOrdersAndLogs(page);

  // /backtests opens the newest backtest.
  await page.goto('/backtests');
  await expect(page).toHaveURL(/\/backtests\/\d+$/);
  await expect(list.locator('a[aria-current="page"]')).toHaveCount(1);
});

test('shows how to save bars when no watchlist instrument has saved bars', async ({ page }) => {
  await page.route('**/api/watchlist', (route) => route.fulfill({ json: { instruments: [] } }));

  await page.goto('/backtests');
  await page.getByRole('button', { name: 'New backtest' }).click();

  const dialog = page.getByRole('dialog', { name: 'New backtest' });
  await expect(dialog.getByRole('combobox', { name: 'Instrument', exact: true })).toBeDisabled();
  const emptyState = dialog.getByRole('status', { name: 'Saved bars' });
  await expect(emptyState).toHaveText(
    'No watchlist instrument has saved 1 day bars. Add an instrument to the watchlist and open its bar chart: the chart saves the bars.',
  );
  await emptyState.getByRole('link', { name: 'watchlist' }).click();
  await expect(page).toHaveURL(/\/$/);
});
