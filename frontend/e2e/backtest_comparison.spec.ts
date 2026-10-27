// Backtest comparison: the list shows metrics side by side, refuses a selection of different strategies, and compares
// two versions of the same strategy (code diff, metric table, both equity curves on one chart). The list scrolls
// inside its own region with a visible track.
import { expect, test, type APIRequestContext } from '@playwright/test';

// A real child process runs each backtest. The browser projects share one queue with concurrency 1.
const BACKTEST_TIMEOUT_MILLISECONDS = 90_000;
// Backtests of a few days run fast. They fill the list, so that it overflows its region. The start route refuses a
// backtest without saved bars, so the filler backtests use the saved AAPL bars too.
const FILLER_BACKTEST_COUNT = 6;
const FULL_RANGE = { startUtc: '2023-01-02T00:00:00Z', endUtc: '2026-01-01T00:00:00Z' };
const FILLER_RANGE = { startUtc: '2023-01-02T00:00:00Z', endUtc: '2023-01-06T00:00:00Z' };
const CHANGED_CODE_LINE = '# Compared version: one more comment line.';

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

test('compares two versions of the same strategy and refuses different strategies', async ({ page, request }, currentTest) => {
  test.setTimeout(BACKTEST_TIMEOUT_MILLISECONDS * 2);
  await page.setViewportSize({ width: 1280, height: 640 });
  // The chart saves the daily bars from 2023-01-02 to 2026-01-01 in PostgreSQL. Backtests read only saved bars.
  await page.goto('/instruments/NASDAQ/AAPL?currency=USD&bar_period=1-DAY');
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('1096 bars');

  // The e2e database is not cleared between tests and browser projects, so the strategy names are unique.
  const suffix = `${currentTest.project.name} ${String(Date.now())}`;
  const compared = await createStrategy(request, `Compared ${suffix}`);
  const other = await createStrategy(request, `Other ${suffix}`);
  const secondVersionResponse = await request.post(`/api/strategies/${String(compared.id)}/versions`, {
    // eslint-disable-next-line @typescript-eslint/naming-convention -- `data` is the request body option of Playwright.
    data: { code: `${compared.version.code}\n${CHANGED_CODE_LINE}\n` },
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

  await page.goto('/backtests');
  const list = page.getByRole('region', { name: 'Backtests' });
  const track = page.getByRole('scrollbar', { name: 'Backtests scroll bar' });
  await expect(list.getByRole('columnheader', { name: 'Final equity (USD)' })).toBeVisible();
  await expect(track).toBeVisible();
  await expect(track.locator('.scroll-thumb')).toBeVisible();

  const selection = page.getByRole('status', { name: 'Comparison selection' });
  const compareButton = page.getByRole('button', { name: 'Compare selected backtests' });
  await list.getByLabel(`Select backtest #${String(firstBacktestId)}`, { exact: true }).check();
  await list.getByLabel(`Select backtest #${String(otherBacktestId)}`, { exact: true }).check();
  await expect(selection).toHaveText(/Only backtests of the same strategy can be compared/);
  await expect(compareButton).toBeDisabled();

  await list.getByLabel(`Select backtest #${String(otherBacktestId)}`, { exact: true }).uncheck();
  await list.getByLabel(`Select backtest #${String(secondBacktestId)}`, { exact: true }).check();
  await expect(selection).toHaveText('Ready to compare.');
  await compareButton.click();

  await expect(page.getByRole('heading', { level: 1 })).toHaveText(
    `Compare backtests #${String(firstBacktestId)} and #${String(secondBacktestId)}`,
  );
  const firstLabel = `#${String(firstBacktestId)} Compared ${suffix} v1`;
  const secondLabel = `#${String(secondBacktestId)} Compared ${suffix} v2`;
  await expect(page.locator('.cm-mergeView')).toContainText(CHANGED_CODE_LINE);
  const metrics = page.getByRole('region', { name: 'Compared metrics' });
  await expect(metrics.getByRole('columnheader', { name: firstLabel })).toBeVisible();
  await expect(metrics.getByRole('columnheader', { name: secondLabel })).toBeVisible();
  await expect(metrics.getByRole('row', { name: /Final equity \(USD\)/ })).toBeVisible();
  await expect(page.getByRole('img', { name: 'Compared equity curves' }).locator('canvas').first()).toBeVisible();
  const legend = page.getByRole('list', { name: 'Compared equity curves legend' });
  await expect(legend.getByRole('listitem')).toHaveText([firstLabel, secondLabel]);

  // The backend also refuses a comparison of different strategies, for example from a typed URL.
  await page.goto(`/backtests/${String(firstBacktestId)}/comparison/${String(otherBacktestId)}`);
  await expect(page.getByRole('alert')).toHaveText(/Only backtests of the same strategy can be compared/);
});
