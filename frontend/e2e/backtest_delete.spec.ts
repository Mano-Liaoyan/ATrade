// A true delete of backtests from the backtest list: Delete in the Carbon batch action bar, a danger dialog, and the
// reason of each backtest that the backend refuses (409). A deleted open backtest leaves the page on the newest one.
import { expect, test, type APIRequestContext } from '@playwright/test';

// A real child process runs each backtest. The browser projects share one queue with concurrency 1.
const BACKTEST_TIMEOUT_MILLISECONDS = 90_000;
const SHORT_RANGE = { start_utc: '2023-01-02T00:00:00Z', end_utc: '2023-01-06T00:00:00Z' };

async function startFinishedBacktest(request: APIRequestContext, name: string): Promise<number> {
  // eslint-disable-next-line @typescript-eslint/naming-convention -- `data` is the request body option of Playwright.
  const strategy = (await (await request.post('/api/strategies', { data: { name } })).json()) as { id: number };
  const version = (await (await request.get(`/api/strategies/${String(strategy.id)}/versions/1`)).json()) as { id: number };
  const response = await request.post('/api/backtests', {
    // eslint-disable-next-line @typescript-eslint/naming-convention -- `data` is the request body option of Playwright.
    data: {
      strategy_version_id: version.id,
      symbol: 'AAPL',
      exchange: 'NASDAQ',
      currency: 'USD',
      bar_period: '1-DAY',
      ...SHORT_RANGE,
      paper_capital_usd: '10000',
    },
  });
  expect(response.status()).toBe(201);
  const backtestId = ((await response.json()) as { id: number }).id;
  await expect
    .poll(
      async () => ((await (await request.get(`/api/backtests/${String(backtestId)}`)).json()) as { status: string }).status,
      { timeout: BACKTEST_TIMEOUT_MILLISECONDS },
    )
    .toBe('finished');
  return backtestId;
}

test('deletes a checked backtest after the danger dialog and shows the reason of a refusal', async ({ page, request }, currentTest) => {
  test.setTimeout(BACKTEST_TIMEOUT_MILLISECONDS * 2);
  // The chart saves the daily AAPL bars in PostgreSQL. Backtests read only saved bars.
  await page.goto('/instruments/NASDAQ/AAPL?currency=USD&bar_period=1-DAY');
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('1096 bars');
  const backtestId = await startFinishedBacktest(request, `Delete ${currentTest.project.name} ${String(Date.now())}`);

  await page.goto(`/backtests/${String(backtestId)}`);
  const list = page.getByRole('complementary', { name: 'Backtests' });
  const row = list.getByRole('row', { name: new RegExp(`#${String(backtestId)} `) });
  await row.getByRole('checkbox', { name: `Select backtest #${String(backtestId)}`, exact: true }).check();
  await expect(list.getByRole('status', { name: 'Comparison selection' })).toHaveText('1 backtest selected');

  // The first delete is refused, for example while the backtest is the same-period backtest of a forward test.
  const refusal = `Backtest #${String(backtestId)} is the same-period backtest of a forward test.`;
  await page.route(`**/api/backtests/${String(backtestId)}`, async (route) => {
    if (route.request().method() !== 'DELETE') {
      await route.continue();
      return;
    }
    await route.fulfill({ status: 409, json: { detail: refusal } });
  });
  await list.getByRole('button', { name: 'Delete', exact: true }).click();
  const dialog = page.getByRole('dialog', { name: `Delete backtest #${String(backtestId)}?` });
  await dialog.getByRole('button', { name: 'Delete backtest', exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await expect(list.getByRole('alert')).toContainText(refusal);
  await expect(row).toBeVisible();

  await page.unroute(`**/api/backtests/${String(backtestId)}`);
  await list.getByRole('button', { name: 'Delete', exact: true }).click();
  await dialog.getByRole('button', { name: 'Cancel', exact: true }).click();
  await expect(row).toBeVisible();
  await list.getByRole('button', { name: 'Delete', exact: true }).click();
  await dialog.getByRole('button', { name: 'Delete backtest', exact: true }).click();
  await expect(row).toHaveCount(0);
  await expect(page).not.toHaveURL(new RegExp(`/backtests/${String(backtestId)}$`));
  expect((await request.get(`/api/backtests/${String(backtestId)}`)).status()).toBe(404);
});
