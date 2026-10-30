// Multi-instrument backtests from the New backtest form (#200): the Instruments select, the N check of Top N, and a
// watchlist backtest with its header label, the Instruments tab, and the Symbol column of the Trades table. The bar
// chart saves the AAPL bars in ibkr_bar, and the watchlist has AAPL.
import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

const BACKTEST_TIMEOUT_MILLISECONDS = 60_000;
const WARNING_TEXT = 'The universe has survivorship bias: instruments that stopped trading are missing.';

async function createStrategy(page: Page, strategyName: string): Promise<void> {
  await page.goto('/strategies');
  await page.getByRole('button', { name: 'New strategy' }).click();
  const dialog = page.getByRole('dialog', { name: 'New strategy' });
  await dialog.getByLabel('Strategy name').fill(strategyName);
  // A universe backtest needs a multi-instrument strategy: its configuration has no instrument_id and no bar_type
  // (docs/architecture/backtest.md, decided in #198). Template M1 is one.
  await dialog.getByRole('listbox', { name: 'Start from' }).getByRole('option', { name: 'Cross-sectional momentum' }).click();
  await dialog.getByRole('button', { name: 'Create strategy' }).click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(strategyName);
}

async function saveAppleBars(page: Page, request: APIRequestContext): Promise<void> {
  await page.goto('/instruments/NASDAQ/AAPL?currency=USD&bar_period=1-DAY');
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('1096 bars');
  // eslint-disable-next-line @typescript-eslint/naming-convention -- `data` is the request body option of Playwright.
  const watchlistResponse = await request.post('/api/watchlist', { data: { symbol: 'AAPL', exchange: 'NASDAQ', currency: 'USD' } });
  expect([201, 409]).toContain(watchlistResponse.status());
}

async function openNewBacktest(page: Page, strategyName: string): Promise<ReturnType<Page['getByRole']>> {
  await page.getByRole('link', { name: 'Backtests' }).click();
  await page.getByRole('button', { name: 'New backtest' }).click();
  const dialog = page.getByRole('dialog', { name: 'New backtest' });
  await dialog.getByRole('combobox', { name: 'Strategy', exact: true }).click();
  await page.getByRole('option', { name: strategyName, exact: true }).click();
  await expect(dialog.getByRole('combobox', { name: 'Strategy version' })).toHaveText(`${strategyName} v1`);
  await dialog.getByRole('combobox', { name: 'Bar period' }).click();
  await page.getByRole('option', { name: '1 day', exact: true }).click();
  return dialog;
}

test('starts a watchlist backtest and sees each instrument and the symbol of each trade', async ({ page, request }, currentTest) => {
  test.setTimeout(BACKTEST_TIMEOUT_MILLISECONDS * 2);
  await saveAppleBars(page, request);
  const strategyName = `Universe ${currentTest.project.name} ${String(Date.now())}`;
  await createStrategy(page, strategyName);
  const dialog = await openNewBacktest(page, strategyName);

  await dialog.getByRole('combobox', { name: 'Instruments' }).click();
  await page.getByRole('option', { name: 'Top N by trading value', exact: true }).click();
  await expect(dialog.getByRole('status', { name: 'Saved bars' })).toContainText('universe data', { ignoreCase: true });
  await dialog.getByLabel('N', { exact: true }).fill('0');
  await expect(dialog.getByRole('button', { name: 'Start backtest' })).toBeDisabled();
  await expect(dialog.getByText('N must be a whole number from 1 to 500.')).toBeVisible();

  await dialog.getByRole('combobox', { name: 'Instruments' }).click();
  await page.getByRole('option', { name: 'Watchlist', exact: true }).click();
  await expect(dialog.getByText(WARNING_TEXT)).toBeVisible();
  await dialog.getByLabel('Start date (UTC)').fill('2025-01-01');
  await dialog.getByLabel('End date (UTC)').fill('2025-01-11');
  await dialog.getByRole('button', { name: 'Start backtest' }).click();

  await expect(page.getByRole('dialog', { name: 'New backtest' })).toHaveCount(0);
  await expect(page).toHaveURL(/\/backtests\/\d+$/);
  const backtestId = page.url().split('/').at(-1) ?? '';
  const chartPanel = page.getByRole('region', { name: `Backtest #${backtestId}` });
  await expect(chartPanel.getByRole('status', { name: 'Backtest status' })).toHaveText('Finished', {
    timeout: BACKTEST_TIMEOUT_MILLISECONDS,
  });
  await expect(chartPanel.getByRole('heading', { level: 1 })).toContainText(/Fixed list \(\d+\)/);

  const tables = page.getByRole('region', { name: 'Backtest tables' });
  await tables.getByRole('tab', { name: 'Instruments' }).click();
  const rows = tables.getByRole('region', { name: 'Instruments' }).getByRole('row');
  await expect(rows.first()).toHaveText(/Instrument\s*Trades\s*Net profit \(USD\)\s*Quarters/);
  const lastRow = rows.last();
  await lastRow.scrollIntoViewIfNeeded();
  await expect(lastRow).toBeInViewport();
  await expect(lastRow.getByRole('cell').last()).toHaveAttribute('align', 'right');
});
