// Backtest: start a backtest of the template strategy on saved bars and see its result. The bar chart saves the
// bars first: the IBKR fake of backend/tests/e2e_server.py has one daily bar for each day, with saw-tooth prices.
import { expect, test } from '@playwright/test';

// A real child process runs each backtest. The browser projects share one queue with concurrency 1.
const BACKTEST_TIMEOUT_MILLISECONDS = 60_000;

test('starts a backtest and sees its metrics, equity curve, and trades', async ({ page }, currentTest) => {
  test.setTimeout(BACKTEST_TIMEOUT_MILLISECONDS * 2);
  // The chart saves the daily bars from 2023-01-02 to 2026-01-01 in PostgreSQL. Backtests read only saved bars.
  await page.goto('/instruments/NASDAQ/AAPL?currency=USD&bar_period=1-DAY');
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('1096 bars');
  // The e2e database is not cleared between tests and browser projects, so the strategy name is unique.
  const strategyName = `Backtest ${currentTest.project.name} ${String(Date.now())}`;
  await page.goto('/strategies');
  await page.getByLabel('Strategy name').fill(strategyName);
  await page.getByRole('button', { name: 'Create strategy' }).click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(strategyName);

  await page.getByRole('link', { name: 'Backtests' }).click();
  // The e2e server paper account balance is the default paper capital.
  await expect(page.getByLabel('Paper capital (USD)')).toHaveValue('101234.50');
  await page.getByLabel('Strategy', { exact: true }).selectOption({ label: strategyName });
  await expect(page.getByLabel('Strategy version')).toHaveValue(/\d+/);
  await page.getByLabel('Symbol').fill('AAPL');
  await page.getByLabel('Exchange').fill('NASDAQ');
  await page.getByLabel('Bar period').selectOption('1-DAY');
  await page.getByLabel('Start date (UTC)').fill('2023-01-02');
  await page.getByLabel('End date (UTC)').fill('2026-01-01');
  await page.getByRole('button', { name: 'Start backtest' }).click();

  await expect(page.getByRole('heading', { level: 1 })).toHaveText(/Backtest #\d+/);
  await expect(page.getByRole('status', { name: 'Backtest status' })).toHaveText('Finished', {
    timeout: BACKTEST_TIMEOUT_MILLISECONDS,
  });
  await expect(page.getByRole('definition').filter({ hasText: `${strategyName} v1` })).toBeVisible();
  const metrics = page.getByLabel('Metrics', { exact: true });
  await expect(metrics).toContainText('Final equity (USD)');
  await expect(metrics).toContainText('Max drawdown');
  await expect(page.getByRole('img', { name: 'Equity curve' }).locator('canvas').first()).toBeVisible();

  const trades = page.getByRole('region', { name: 'Trades' });
  const track = page.getByRole('scrollbar', { name: 'Trades scroll bar' });
  const lastRow = trades.getByRole('row').last();
  await trades.scrollIntoViewIfNeeded();
  await expect(track).toBeVisible();
  await expect(track.locator('.scroll-thumb')).toBeVisible();
  await expect(lastRow).not.toBeInViewport();

  await track.focus();
  await page.keyboard.press('End');

  await expect(lastRow).toBeInViewport();
  await expect(track).toHaveAttribute('aria-valuenow', '100');
});
