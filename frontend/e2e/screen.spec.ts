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

// #212: the edit popover of each tag, "Add condition", the run at once after each change, and the save buttons.
type Locator = ReturnType<Page['getByRole']>;

const conditionBar = (page: Page): Locator => page.getByRole('list', { name: 'Conditions' });

// A change runs the screen at once. The funnel counts show again when the screen result of the change is there.
async function expectRunDone(page: Page): Promise<void> {
  await expect(conditionBar(page).getByLabel('Order count')).toBeVisible();
}

async function addCondition(page: Page, kind: string): Promise<void> {
  await page.getByRole('button', { name: 'Add condition', exact: true }).click();
  await page.getByRole('menuitem', { name: kind, exact: true }).click();
  await page.getByRole('dialog', { name: 'Edit condition' }).getByRole('button', { name: 'Add condition' }).click();
}

async function editTag(page: Page, tag: string): Promise<Locator> {
  await page.getByRole('button', { name: `Edit ${tag}`, exact: true }).click();
  const popover = page.getByRole('dialog', { name: 'Edit condition' });
  await expect(popover).toBeVisible();
  return popover;
}

async function selectOption(page: Page, popover: Locator, field: string, option: string): Promise<void> {
  await popover.getByRole('combobox', { name: field, exact: true }).click();
  await page.getByRole('option', { name: option, exact: true }).click();
}

async function applyAndWait(page: Page, popover: Locator, tag: string): Promise<void> {
  await popover.getByRole('button', { name: 'Apply' }).click();
  await expect(page.getByRole('button', { name: `Edit ${tag}`, exact: true })).toBeVisible();
  await expectRunDone(page);
}

async function openNewScreen(
  page: Page,
  request: APIRequestContext,
  name: string,
  definition: Record<string, unknown>,
): Promise<number> {
  await saveAaplDailyBars(page, request);
  const screenId = await createScreen(request, name, 'US', definition);
  await runScreen(request, screenId);
  await page.goto(`/screens/${String(screenId)}`);
  await expectRunDone(page);
  await expect(page.getByRole('button', { name: 'Save screen' })).toHaveCount(0);
  return screenId;
}

test('adds and changes each kind of condition and the order, and runs at once', async ({ page, request }, currentTest) => {
  await openNewScreen(page, request, uniqueName(currentTest, 'Edit'), {
    start: 'watchlist',
    filters: [{ field: 'last_price', operator: '>', value: '0' }],
    indicator_conditions: [],
    order: { indicator: SMA_3, direction: 'descending' },
  });

  const added: [string, string][] = [
    ['Still trading', 'Still trading'],
    ['Avg trading value (20)', 'Avg trading value (20) ≥ 20,000,000'],
    ['Exchange', 'Exchange in NASDAQ, NYSE'],
    ['Indicator', 'RSI(14) < 30'],
    ['Close vs line', 'Close above SMA(200)'],
    ['Rank', '12-1 momentum(252, 21) top 20%'],
  ];
  for (const [kind, tag] of added) {
    await addCondition(page, kind);
    await expect(page.getByRole('button', { name: `Edit ${tag}`, exact: true })).toBeVisible();
    await expectRunDone(page);
  }
  await expect(page.getByRole('button', { name: 'Save screen' })).toBeVisible();

  let popover = await editTag(page, 'Close > 0');
  await popover.getByLabel('Value').fill('1');
  await applyAndWait(page, popover, 'Close > 1');

  popover = await editTag(page, 'RSI(14) < 30');
  await popover.getByLabel('Period').fill('10');
  await selectOption(page, popover, 'Operator', '≥');
  await popover.getByLabel('Value').fill('0');
  await applyAndWait(page, popover, 'RSI(10) ≥ 0');

  popover = await editTag(page, 'Close above SMA(200)');
  await selectOption(page, popover, 'Close', 'below');
  await selectOption(page, popover, 'Line', 'EMA');
  await applyAndWait(page, popover, 'Close below EMA(20)');

  popover = await editTag(page, '12-1 momentum(252, 21) top 20%');
  await selectOption(page, popover, 'Keep', 'Bottom');
  await popover.getByLabel('%').fill('50');
  await applyAndWait(page, popover, '12-1 momentum(252, 21) bottom 50%');

  popover = await editTag(page, 'SMA(3) descending');
  await selectOption(page, popover, 'Direction', 'Low first');
  await popover.getByLabel('First').fill('5');
  await applyAndWait(page, popover, 'SMA(3) ascending first 5');

  popover = await editTag(page, 'Watchlist');
  await selectOption(page, popover, 'Instruments', 'All with daily bars');
  await applyAndWait(page, popover, 'All with daily bars');
});

test('shows a 422 problem at its tag, removes conditions, keeps the saved screen until a save, and saves as new', async ({
  page,
  request,
}, currentTest) => {
  const name = uniqueName(currentTest, 'Save');
  const filters = [
    { field: 'last_price', operator: '>', value: '0' },
    { field: 'exchange', values: ['NASDAQ', 'NYSE'] },
  ];
  const screenId = await openNewScreen(page, request, name, {
    start: 'watchlist',
    filters,
    indicator_conditions: [{ kind: 'compare', indicator: { indicator: 'rsi', parameters: { period: 14 }, output: 'value' }, operator: '>=', value: '0' }],
    order: { indicator: SMA_3, direction: 'descending' },
  });
  const bar = conditionBar(page);
  const saveScreen = page.getByRole('button', { name: 'Save screen' });

  // A parameter out of its range: the problem shows next to its tag, and the funnel counts go.
  const popover = await editTag(page, 'RSI(14) ≥ 0');
  await popover.getByLabel('Period').fill('0');
  await popover.getByRole('button', { name: 'Apply' }).click();
  await expect(bar.getByRole('alert')).toContainText('period');
  await expect(bar.getByLabel('Order count')).toHaveCount(0);

  // Remove with the × button and with the Remove button of the popover.
  await page.getByRole('button', { name: 'Remove RSI(0) ≥ 0', exact: true }).click();
  await expect(bar.getByRole('alert')).toHaveCount(0);
  await expectRunDone(page);
  await (await editTag(page, 'Exchange in NASDAQ, NYSE')).getByRole('button', { name: 'Remove' }).click();
  await expect(bar).not.toContainText('Exchange');
  await expectRunDone(page);

  // The runs did not change the saved screen.
  const saved = (await (await request.get(`/api/screens/${String(screenId)}`)).json()) as { definition: { filters: unknown[] } };
  expect(saved.definition.filters).toEqual(filters);

  await saveScreen.click();
  await expect(saveScreen).toHaveCount(0);
  await page.reload();
  await expect(page.getByRole('button', { name: 'Edit Close > 0', exact: true })).toBeVisible();
  await expect(bar).not.toContainText('Exchange');
  await expect(bar).not.toContainText('RSI');

  // A market switch makes a draft that only "Save as new screen" saves.
  await page.getByRole('tablist', { name: 'Market' }).getByRole('tab', { name: 'HK' }).click();
  await expect(page.getByRole('button', { name: 'Edit HK instrument list', exact: true })).toBeVisible();
  await expectRunDone(page);
  await expect(saveScreen).toHaveCount(0);
  await page.getByRole('button', { name: 'Save as new screen' }).click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(`${name} copy`);
  await expect(page.getByRole('region', { name: 'Screen list' })).toContainText(`${name} copy`);
  await expect(page.getByText('The universe has survivorship bias', { exact: false })).toBeVisible();
});
