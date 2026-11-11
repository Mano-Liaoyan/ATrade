// Backtest rerun (docs/architecture/backtest.md sections 10.5 and 10.6): after a change of the strategy, a backtest of
// the new version runs on the data of an earlier backtest, without the New backtest dialog. The strategy page reruns
// the shown backtest tab with the open version. The backtest page reruns the open backtest with the latest version.
import { expect, test, type APIRequestContext } from '@playwright/test';
import { waitForStartedRunId } from './started_run';

// A real child process runs each backtest. The browser projects share one queue with concurrency 1.
const BACKTEST_TIMEOUT_MILLISECONDS = 60_000;

interface StrategyVersion {
  id: number;
  code: string;
}

async function readVersion(request: APIRequestContext, strategyId: string, versionNumber: number): Promise<StrategyVersion> {
  const response = await request.get(`/api/strategies/${strategyId}/versions/${String(versionNumber)}`);
  return (await response.json()) as StrategyVersion;
}

test('reruns a backtest with the new strategy version on the same data', async ({ page, request }, currentTest) => {
  test.setTimeout(BACKTEST_TIMEOUT_MILLISECONDS * 4);
  // The chart saves the daily bars in PostgreSQL. Backtests read only saved bars.
  await page.goto('/instruments/NASDAQ/AAPL?currency=USD&bar_period=1-DAY');
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('1096 bars');
  const strategyName = `Rerun ${currentTest.project.name} ${String(Date.now())}`;
  await page.goto('/strategies');
  await page.getByRole('button', { name: 'New strategy' }).click();
  await page.getByLabel('Strategy name').fill(strategyName);
  await page.getByRole('button', { name: 'Create strategy' }).click();
  await expect(page).toHaveURL(/\/strategies\/\d+$/);
  const strategyId = page.url().split('/').at(-1) ?? '';
  const firstVersion = await readVersion(request, strategyId, 1);
  /* eslint-disable @typescript-eslint/naming-convention -- `data` is the request body option of Playwright. */
  const started = await request.post('/api/backtests', {
    data: {
      strategy_version_id: firstVersion.id,
      symbol: 'AAPL',
      exchange: 'NASDAQ',
      currency: 'USD',
      bar_period: '1-DAY',
      start_utc: '2024-01-01T00:00:00Z',
      end_utc: '2025-01-01T00:00:00Z',
      paper_capital_usd: '20000',
      out_of_sample_share: 10,
    },
  });
  expect(started.status()).toBe(201);
  const firstBacktest = (await started.json()) as Record<string, unknown>;
  const firstId = String(firstBacktest['id']);
  // The change of the strategy: version 2.
  const saved = await request.post(`/api/strategies/${strategyId}/versions`, {
    data: { code: `${firstVersion.code}\n# Changed.\n` },
  });
  /* eslint-enable @typescript-eslint/naming-convention */
  expect(saved.status()).toBe(201);

  // The strategy page opens version 2. The shown backtest tab is #<first>.
  await page.reload();
  const results = page.getByRole('region', { name: 'Results' });
  await expect(results.getByRole('tab', { name: new RegExp(`^Finished Backtest #${firstId}\\b`) })).toBeVisible({
    timeout: BACKTEST_TIMEOUT_MILLISECONDS,
  });
  const strategyRerunId = waitForStartedRunId(page, `/api/backtests/${firstId}/rerun`);
  await page.getByRole('button', { name: `Rerun backtest #${firstId} with v2` }).click();
  const secondId = await strategyRerunId;
  await expect(results.getByRole('tab', { name: new RegExp(`Backtest #${secondId}\\b`), selected: true })).toBeVisible();
  const second = (await (await request.get(`/api/backtests/${secondId}`)).json()) as Record<string, unknown>;
  for (const field of ['symbol', 'exchange', 'bar_period', 'start_utc', 'end_utc', 'paper_capital_usd', 'out_of_sample_share']) {
    expect(second[field], field).toEqual(firstBacktest[field]);
  }
  expect(second['version_number']).toBe(2);

  // The backtest page reruns the open backtest with the latest version: v2.
  await page.goto(`/backtests/${firstId}`);
  const backtestRerunId = waitForStartedRunId(page, `/api/backtests/${firstId}/rerun`);
  await page.getByRole('region', { name: `Backtest #${firstId}` }).getByRole('button', { name: 'Rerun backtest with v2' }).click();
  const thirdId = await backtestRerunId;
  await expect(page).toHaveURL(new RegExp(`/backtests/${thirdId}$`));
  await expect(
    page.getByRole('region', { name: `Backtest #${thirdId}` }).getByRole('heading', { level: 1 }).getByRole('link', { name: `${strategyName} v2` }),
  ).toBeVisible();
});
