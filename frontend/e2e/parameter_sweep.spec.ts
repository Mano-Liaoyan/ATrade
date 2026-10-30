// Parameter sweep page (#204): start a sweep of 2 parameters of the template strategy from the "New parameter sweep"
// dialog, see the heatmap and the "Metric" select, sort the Runs table, scroll to its last row, and open the backtest
// of a run, which links back to its sweep. The bar chart saves the AAPL bars first, and the watchlist has AAPL.
import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

// A real child process runs each run. The browser projects share one queue with concurrency 1.
const RUN_TIMEOUT_MILLISECONDS = 90_000;

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
  // eslint-disable-next-line @typescript-eslint/naming-convention -- `data` is the request body option of Playwright.
  const watchlistResponse = await request.post('/api/watchlist', { data: { symbol: 'AAPL', exchange: 'NASDAQ', currency: 'USD' } });
  expect([201, 409]).toContain(watchlistResponse.status());
}

async function setRange(page: Page, parameter: string, range: [string, string, string]): Promise<void> {
  const dialog = page.getByRole('dialog', { name: 'New parameter sweep' });
  await dialog.getByLabel(`Start of ${parameter}`).fill(range[0]);
  await dialog.getByLabel(`End of ${parameter}`).fill(range[1]);
  await dialog.getByLabel(`Step of ${parameter}`).fill(range[2]);
}

test('starts a parameter sweep, sorts its runs, and opens the backtest of a run', async ({ page, request }, currentTest) => {
  test.setTimeout(RUN_TIMEOUT_MILLISECONDS * 2);
  await saveAppleBars(page, request);
  const strategyName = `Sweep ${currentTest.project.name} ${String(Date.now())}`;
  await createStrategy(page, strategyName);

  await page.getByRole('banner').getByRole('link', { name: 'Parameter sweeps' }).click();
  await page.getByRole('button', { name: 'New parameter sweep' }).click();
  const dialog = page.getByRole('dialog', { name: 'New parameter sweep' });
  await dialog.getByRole('combobox', { name: 'Strategy', exact: true }).click();
  await page.getByRole('option', { name: strategyName, exact: true }).click();
  await expect(dialog.getByRole('combobox', { name: 'Strategy version' })).toHaveText(`${strategyName} v1`);
  await dialog.getByRole('combobox', { name: 'Bar period' }).click();
  await page.getByRole('option', { name: '1 day', exact: true }).click();
  await dialog.getByRole('combobox', { name: 'Instrument', exact: true }).click();
  await page.getByRole('option', { name: 'AAPL / NASDAQ / USD', exact: true }).click();
  await dialog.getByLabel('Start date (UTC)').fill('2025-01-01');
  await dialog.getByLabel('End date (UTC)').fill('2025-01-11');

  const runCount = dialog.getByRole('status', { name: 'Run count' });
  const startButton = dialog.getByRole('button', { name: 'Start parameter sweep' });
  await expect(runCount).toContainText('Select 1 to 3 parameters to sweep.');
  await expect(startButton).toBeDisabled();
  await dialog.getByRole('checkbox', { name: 'Sweep average_period' }).check();
  await setRange(page, 'average_period', ['1', '300', '1']);
  await expect(runCount).toHaveText(/300 runs\s*The grid has 300 runs\. The limit is 200\./);
  await expect(startButton).toBeDisabled();
  await setRange(page, 'average_period', ['10', '15', '5']);
  await dialog.getByRole('checkbox', { name: 'Sweep trade_quantity_shares' }).check();
  await setRange(page, 'trade_quantity_shares', ['5', '10', '5']);
  await expect(runCount).toHaveText('4 runs');
  // /sweeps already opened the newest sweep of an earlier test, so the page waits for the new sweep ID.
  const startResponse = page.waitForResponse(
    (response) => response.url().endsWith('/api/sweeps') && response.request().method() === 'POST',
  );
  await startButton.click();
  const sweepId = String(((await (await startResponse).json()) as { id: number }).id);

  await expect(page).toHaveURL(new RegExp(`/sweeps/${sweepId}$`));
  try {
    const overview = page.getByRole('region', { name: `Parameter sweep #${sweepId}` });
    await expect(overview.getByRole('status', { name: 'Run counts' })).toContainText(/[1-4] finished/, {
      timeout: RUN_TIMEOUT_MILLISECONDS,
    });
    const heatmap = overview.getByRole('table', { name: 'Total return heatmap' });
    await expect(heatmap.getByRole('cell', { name: /^[+-]?\d+\.\d{2} %$/ }).first()).toBeVisible();
    await overview.getByRole('combobox', { name: 'Metric' }).click();
    await page.getByRole('option', { name: 'Trades', exact: true }).click();
    const tradesHeatmap = overview.getByRole('table', { name: 'Trades heatmap' });
    await expect(tradesHeatmap.getByRole('cell', { name: /^\d+$/ }).first()).toBeVisible();

    const runs = page.getByRole('region', { name: 'Runs' });
    const periodHeader = runs.getByRole('columnheader', { name: 'average_period' });
    await periodHeader.getByRole('button').click();
    await expect(periodHeader).toHaveAttribute('aria-sort', 'descending');
    const rows = runs.getByRole('row');
    await expect(rows.nth(1).getByRole('cell').first()).toHaveText('15');
    await periodHeader.getByRole('button').click();
    await expect(periodHeader).toHaveAttribute('aria-sort', 'ascending');
    await expect(rows.nth(1).getByRole('cell').first()).toHaveText('10');
    const lastRow = rows.last();
    await lastRow.scrollIntoViewIfNeeded();
    await expect(lastRow).toBeInViewport();
    await expect(lastRow.getByRole('cell').last()).toHaveAttribute('align', 'right');

    await lastRow.getByRole('cell').nth(1).click();
    await expect(page).toHaveURL(/\/backtests\/\d+$/);
    await page.getByRole('link', { name: `Parameter sweep #${sweepId}` }).click();
    await expect(page).toHaveURL(new RegExp(`/sweeps/${sweepId}$`));
  } finally {
    // The other specs share the backtest queue: the queued runs of this sweep must not wait in it.
    await request.post(`/api/sweeps/${sweepId}/cancel`);
  }
});
