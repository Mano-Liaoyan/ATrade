// Bar sources of a backtest (#197): the New backtest form changes the source order of one backtest, the Bar sources
// tab shows the source order and the bar count of each bar source, and an HK backtest shows the survivorship bias
// warning. The bar chart saves the AAPL bars in ibkr_bar: Databento has no bars in the e2e database.
// backend/tests/e2e_server.py adds a failed HK backtest (700) and a failed US backtest of 2026 (SBUS).
import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

// A real child process runs each backtest. The browser projects share one queue with concurrency 1.
const BACKTEST_TIMEOUT_MILLISECONDS = 60_000;
const WARNING_TEXT = 'The universe has survivorship bias: instruments that stopped trading are missing.';

async function createStrategy(page: Page, strategyName: string): Promise<void> {
  await page.goto('/strategies');
  await page.getByRole('button', { name: 'New strategy' }).click();
  await page.getByLabel('Strategy name').fill(strategyName);
  await page.getByRole('button', { name: 'Create strategy' }).click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(strategyName);
}

async function saveAppleBars(page: Page, request: APIRequestContext): Promise<void> {
  await page.goto('/instruments/NASDAQ/AAPL?currency=USD&bar_period=1-DAY');
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('1096 bars');
  // The browser projects share one database: another project can add AAPL first (409).
  // eslint-disable-next-line @typescript-eslint/naming-convention -- `data` is the request body option of Playwright.
  const watchlistResponse = await request.post('/api/watchlist', { data: { symbol: 'AAPL', exchange: 'NASDAQ', currency: 'USD' } });
  expect([201, 409]).toContain(watchlistResponse.status());
}

async function findBacktestId(request: APIRequestContext, symbol: string): Promise<number> {
  const backtests = (await (await request.get('/api/backtests')).json()) as { id: number; symbol: string }[];
  const found = backtests.find((backtest) => backtest.symbol === symbol);
  expect(found).toBeDefined();
  return found?.id ?? 0;
}

test('starts a backtest with a changed source order and sees the bar count of each bar source', async ({ page, request }, currentTest) => {
  test.setTimeout(BACKTEST_TIMEOUT_MILLISECONDS * 2);
  await saveAppleBars(page, request);
  // The e2e database is not cleared between tests and browser projects, so the strategy name is unique.
  const strategyName = `Bar sources ${currentTest.project.name} ${String(Date.now())}`;
  await createStrategy(page, strategyName);

  await page.getByRole('link', { name: 'Backtests' }).click();
  await page.getByRole('button', { name: 'New backtest' }).click();
  const dialog = page.getByRole('dialog', { name: 'New backtest' });
  const sourceOrder = dialog.getByRole('combobox', { name: 'Source order' });
  await expect(sourceOrder).toHaveText('IBKR, Databento');
  await sourceOrder.click();
  await page.getByRole('option', { name: 'Databento, IBKR', exact: true }).click();
  await dialog.getByRole('combobox', { name: 'Strategy', exact: true }).click();
  await page.getByRole('option', { name: strategyName, exact: true }).click();
  await expect(dialog.getByRole('combobox', { name: 'Strategy version' })).toHaveText(`${strategyName} v1`);
  await dialog.getByRole('combobox', { name: 'Bar period' }).click();
  await page.getByRole('option', { name: '1 day', exact: true }).click();
  await dialog.getByRole('combobox', { name: 'Instrument', exact: true }).click();
  await page.getByRole('option', { name: 'AAPL / NASDAQ / USD', exact: true }).click();
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
  // A US backtest of 2025 has no survivorship bias warning.
  await expect(chartPanel.getByText(WARNING_TEXT)).toHaveCount(0);

  const tables = page.getByRole('region', { name: 'Backtest tables' });
  await tables.getByRole('tab', { name: 'Bar sources' }).click();
  // The source order of the form, then the bar counts: the 10 daily AAPL bars are in ibkr_bar only.
  const rows = tables.getByRole('region', { name: 'Bar sources' }).getByRole('row');
  await expect(rows).toHaveText([/Bar source\s*Bars/, /Databento\s*0/, /IBKR\s*10/]);
  await expect(rows.nth(2).getByRole('cell').last()).toHaveAttribute('align', 'right');
});

test('shows the survivorship bias warning on an HK backtest only', async ({ page, request }) => {
  const hkBacktestId = await findBacktestId(request, '700');
  await page.goto(`/backtests/${String(hkBacktestId)}`);
  const hkPanel = page.getByRole('region', { name: `Backtest #${String(hkBacktestId)}` });
  const warning = hkPanel.getByRole('alert').filter({ hasText: WARNING_TEXT });
  await expect(warning).toBeVisible();
  await expect(warning.locator('svg').first()).toBeVisible();

  const usBacktestId = await findBacktestId(request, 'SBUS');
  await page.goto(`/backtests/${String(usBacktestId)}`);
  const usPanel = page.getByRole('region', { name: `Backtest #${String(usBacktestId)}` });
  await expect(usPanel.getByRole('heading', { level: 1 })).toContainText('SBUS');
  await expect(usPanel.getByText(WARNING_TEXT)).toHaveCount(0);
});
