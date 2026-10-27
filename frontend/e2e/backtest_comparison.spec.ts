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
// More changed lines than the code difference region shows, so that it scrolls with a visible track.
const ADDED_COMMENT_LINES = Array.from({ length: 40 }, (_, index) => `# Added line ${String(index + 1)}.`).join('\n');

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

  await page.goto('/backtests');
  const list = page.getByRole('region', { name: 'Backtests' });
  const track = page.getByRole('scrollbar', { name: 'Backtests scroll bar' });
  await expect(list.getByRole('columnheader', { name: 'Final equity (USD)' })).toBeVisible();
  await expect(track).toBeVisible();
  await expect(track.locator('.scroll-thumb')).toBeVisible();

  const selection = page.getByRole('status', { name: 'Comparison selection' });
  const compareButton = page.getByRole('button', { name: 'Compare selected backtests' });
  // A Carbon checkbox draws its box with its label, so the label takes the pointer: force skips that check only.
  await list.getByLabel(`Select backtest #${String(firstBacktestId)}`, { exact: true }).check({ force: true });
  await list.getByLabel(`Select backtest #${String(otherBacktestId)}`, { exact: true }).check({ force: true });
  await expect(selection).toHaveText(/Only backtests of the same strategy can be compared/);
  await expect(compareButton).toBeDisabled();

  await list.getByLabel(`Select backtest #${String(otherBacktestId)}`, { exact: true }).uncheck({ force: true });
  await list.getByLabel(`Select backtest #${String(secondBacktestId)}`, { exact: true }).check({ force: true });
  await expect(selection).toHaveText('Ready to compare.');
  await compareButton.click();

  await expect(page.getByRole('heading', { level: 1 })).toHaveText(
    `Compare backtests #${String(firstBacktestId)} and #${String(secondBacktestId)}`,
  );
  const firstLabel = `#${String(firstBacktestId)} Compared ${suffix} v1`;
  const secondLabel = `#${String(secondBacktestId)} Compared ${suffix} v2`;
  await expect(page.locator('.cm-mergeView')).toContainText(CHANGED_CODE_LINE);
  // Only the changed lines and a few lines around them show. The unchanged lines are collapsed.
  await expect(page.locator('.cm-collapsedLines').first()).toBeVisible();
  await expect(page.locator('.cm-mergeView')).not.toContainText('class MovingAverageStrategy(Strategy):');
  const diffTrack = page.getByRole('scrollbar', { name: 'Code difference scroll bar' });
  await expect(diffTrack).toBeVisible();
  await expect(diffTrack.locator('.scroll-thumb')).toBeVisible();
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

test('shows a note instead of an empty code difference for the same strategy version', async ({ page, request }, currentTest) => {
  // The chart saves the daily bars in PostgreSQL. The start route refuses a backtest without saved bars.
  await page.goto('/instruments/NASDAQ/AAPL?currency=USD&bar_period=1-DAY');
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('1096 bars');
  const compared = await createStrategy(request, `Same version ${currentTest.project.name} ${String(Date.now())}`);
  const firstBacktestId = await startBacktest(request, compared.version.id, FILLER_RANGE);
  const secondBacktestId = await startBacktest(request, compared.version.id, FILLER_RANGE);

  await page.goto(`/backtests/${String(firstBacktestId)}/comparison/${String(secondBacktestId)}`);

  await expect(page.getByRole('status', { name: 'Code difference' })).toHaveText(
    'Same strategy version: no code difference.',
  );
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
