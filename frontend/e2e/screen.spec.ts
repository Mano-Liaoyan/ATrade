// Screen page (#207, docs/architecture/screen.md section 24.10): the "Screens" side column, the read-only condition
// bar with its funnel counts, the Result / Excluded switch, the batch "Add to watchlist", and the HK survivorship
// bias warning. The tests make the screens and their screen results with the API. The bar chart saves the daily
// bars of AAPL first: the IBKR fake of backend/tests/e2e_server.py has one daily bar for each day.
import { expect, test, type APIRequestContext, type Page, type TestInfo } from '@playwright/test';

interface ScreenResultSummary {
  start_count: number;
  after_filters_count: number;
  after_indicator_conditions_count: number;
  result_count: number;
}

const SMA_3 = { indicator: 'sma', parameters: { period: 3 }, output: 'value' };

function uniqueName(currentTest: TestInfo, name: string): string {
  // The e2e database is not cleared between tests and browser projects.
  return `${name} ${currentTest.project.name} ${String(Date.now())}`;
}

async function createScreen(
  request: APIRequestContext,
  name: string,
  market: 'US' | 'HK',
  definition: Record<string, unknown>,
): Promise<number> {
  // eslint-disable-next-line @typescript-eslint/naming-convention -- `data` is the request body option of Playwright.
  const response = await request.post('/api/screens', { data: { name, market, definition } });
  expect(response.status()).toBe(201);
  return ((await response.json()) as { id: number }).id;
}

async function runScreen(request: APIRequestContext, screenId: number): Promise<ScreenResultSummary> {
  const response = await request.post(`/api/screens/${String(screenId)}/runs`);
  expect(response.status()).toBe(201);
  return ((await response.json()) as { summary: ScreenResultSummary }).summary;
}

async function saveAaplDailyBars(page: Page, request: APIRequestContext): Promise<void> {
  await page.goto('/instruments/NASDAQ/AAPL?currency=USD&bar_period=1-DAY');
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('1096 bars');
  // eslint-disable-next-line @typescript-eslint/naming-convention -- `data` is the request body option of Playwright.
  const response = await request.post('/api/watchlist', { data: { symbol: 'AAPL', exchange: 'NASDAQ', currency: 'USD' } });
  expect([201, 409]).toContain(response.status());
}

test('shows the condition bar with funnel counts, both tables, and adds selected rows to the watchlist', async ({
  page,
  request,
}, currentTest) => {
  await saveAaplDailyBars(page, request);
  const name = uniqueName(currentTest, 'Screen');
  const screenId = await createScreen(request, name, 'US', {
    start: 'watchlist',
    filters: [{ field: 'last_price', operator: '>', value: '0' }],
    indicator_conditions: [{ kind: 'rank', indicator: SMA_3, end: 'top', percent: 100 }],
    order: { indicator: SMA_3, direction: 'descending' },
  });
  const summary = await runScreen(request, screenId);

  await page.goto(`/screens/${String(screenId)}`);

  await expect(page.getByRole('heading', { level: 1 })).toHaveText(name);
  const bar = page.getByRole('list', { name: 'Conditions' });
  await expect(bar.getByLabel('Start instruments count')).toHaveText(String(summary.start_count));
  await expect(bar.getByLabel('Filters count')).toHaveText(String(summary.after_filters_count));
  await expect(bar.getByLabel('Indicator conditions count')).toHaveText(String(summary.after_indicator_conditions_count));
  await expect(bar.getByLabel('Order count')).toHaveText(String(summary.result_count));
  await expect(bar).toContainText('Close > 0');
  await expect(bar).toContainText('SMA(3) top 100%');
  await expect(page.getByText('Survivorship bias', { exact: false })).toHaveCount(0);

  const results = page.getByRole('region', { name: 'Result table' });
  for (const header of ['#', 'Symbol', 'Exchange', 'Close', 'Avg trading value (20)', 'SMA(3)', 'Percentile']) {
    await expect(results.getByRole('columnheader', { name: header, exact: true })).toBeVisible();
  }
  await expect(results.getByRole('cell', { name: 'AAPL', exact: true })).toBeVisible();

  const switcher = page.getByRole('tablist', { name: 'Screen result table' });
  await switcher.getByRole('tab', { name: /^Excluded \d+$/ }).click();
  await expect(page.getByRole('region', { name: 'Excluded table' })).toBeVisible();
  await switcher.getByRole('tab', { name: `Result ${String(summary.result_count)}` }).click();

  await results.getByRole('checkbox', { name: 'Select AAPL' }).check();
  await expect(page.getByRole('status').filter({ hasText: '1 selected' })).toBeVisible();
  await page.getByRole('button', { name: 'Add to watchlist' }).click();
  // AAPL is in the watchlist already, so the add route can refuse it (409).
  await expect(page.getByText(/^Added \d+ (of \d+ )?instruments to the watchlist/)).toBeVisible();
});

test('an HK screen shows the survivorship bias warning', async ({ page, request }, currentTest) => {
  const screenId = await createScreen(request, uniqueName(currentTest, 'HK screen'), 'HK', {
    start: 'hk_instrument_list',
    filters: [],
    indicator_conditions: [],
    order: { indicator: SMA_3, direction: 'descending' },
  });
  await runScreen(request, screenId);

  await page.goto(`/screens/${String(screenId)}`);

  await expect(page.getByText('The universe has survivorship bias', { exact: false })).toBeVisible();
});

test('/screens opens the last opened screen, and a long screen list scrolls in its own track', async ({
  page,
  request,
}, currentTest) => {
  const definition = { start: 'watchlist', filters: [], indicator_conditions: [], order: { indicator: SMA_3, direction: 'descending' } };
  const screenIds: number[] = [];
  for (let index = 0; index < 30; index += 1) {
    screenIds.push(await createScreen(request, uniqueName(currentTest, `List ${String(index)}`), 'US', definition));
  }
  await page.setViewportSize({ width: 1280, height: 720 });
  const firstId = screenIds[0] ?? 0;
  await page.goto(`/screens/${String(firstId)}`);
  await expect(page.getByRole('heading', { level: 1 })).toContainText('List 0');

  await page.getByRole('link', { name: 'Screens', exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/screens/${String(firstId)}$`));

  const list = page.getByRole('region', { name: 'Screen list' });
  // The list has the last changed screen first; other projects can add screens before ours, not after.
  const lastScreen = list.getByRole('listitem').last();
  await expect(lastScreen).not.toBeInViewport();
  const scrollTrack = page.getByRole('scrollbar', { name: 'Screen list scroll bar' });
  await expect(scrollTrack).toBeVisible();
  await scrollTrack.focus();
  await page.keyboard.press('End');
  await expect(lastScreen).toBeInViewport();
  await expect(scrollTrack).toHaveAttribute('aria-valuenow', '100');
});
