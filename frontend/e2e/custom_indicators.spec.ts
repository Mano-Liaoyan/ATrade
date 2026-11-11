// Custom indicators (docs/architecture/indicator.md section 23.10). The Playwright projects run at the same time against
// one database, and other tests count the catalog, so these tests keep the custom indicators in the browser context. The
// series route is the real backend.
import { expect, test, type APIRequestContext, type BrowserContext, type Route } from '@playwright/test';
import { useLocalChartIndicatorSet } from './local_chart_indicator_set';

const CHART_PATH = '/instruments/SEHK/700?currency=HKD&bar_period=1-DAY';
const FORMULA = { name: 'Close ratio', expression: 'close / sma(20)', chart_placement: 'own' };

const CUSTOM_ITEM = {
  key: 'custom_1',
  name: FORMULA.name,
  short_name: FORMULA.name,
  chart_placement: 'own',
  parameters: [],
  outputs: ['value'],
  value_description: 'The close over SMA(20).',
};

interface Row {
  custom_indicator_id: number;
  key: string;
  name: string;
  expression: string;
  chart_placement: string;
  value_description: string;
  parameters?: unknown[];
  kept: boolean;
  assistant_conversation_id: number | null;
}

async function createScreenWithRun(request: APIRequestContext, name: string, definition: Record<string, unknown>): Promise<number> {
  // eslint-disable-next-line @typescript-eslint/naming-convention -- `data` is the request body option of Playwright.
  const created = await request.post('/api/screens', { data: { name, market: 'US', definition } });
  expect(created.status()).toBe(201);
  const screenId = ((await created.json()) as { id: number }).id;
  expect((await request.post(`/api/screens/${String(screenId)}/runs`)).status()).toBe(201);
  return screenId;
}

async function readVersionCode(request: APIRequestContext, strategyId: string, versionNumber: number): Promise<string> {
  const response = await request.get(`/api/strategies/${strategyId}/versions/${String(versionNumber)}`);
  return ((await response.json()) as { code: string }).code;
}

async function useLocalCustomIndicators(context: BrowserContext, firstRows: Row[] = []): Promise<void> {
  let rows = firstRows;
  let nextId = 1;

  async function answerRequest(route: Route): Promise<void> {
    const request = route.request();
    const id = /\/(\d+)$/.exec(new URL(request.url()).pathname)?.[1];
    if (request.method() === 'GET') {
      await route.fulfill({ json: rows });
      return;
    }
    const keptId = /\/(\d+)\/keep$/.exec(new URL(request.url()).pathname)?.[1];
    if (keptId !== undefined) {
      rows = rows.map((row) => (String(row.custom_indicator_id) === keptId ? { ...row, kept: true } : row));
      await route.fulfill({ json: rows[0] });
      return;
    }
    if (request.method() === 'DELETE') {
      rows = rows.filter((row) => String(row.custom_indicator_id) !== id);
      await route.fulfill({ status: 204 });
      return;
    }
    const fields = request.postDataJSON() as Omit<Row, 'custom_indicator_id' | 'key' | 'kept' | 'assistant_conversation_id'>;
    if (fields.expression === 'foo') {
      const problem = { location: ['expression'], message: "Column 1: Unknown name 'foo'." };
      await route.fulfill({ status: 422, json: { problems: [problem] } });
      return;
    }
    const row = { ...fields, custom_indicator_id: id === undefined ? nextId : Number(id), key: `custom_${id ?? String(nextId)}`, kept: true, assistant_conversation_id: null };
    nextId += 1;
    rows = [...rows.filter((item) => item.custom_indicator_id !== row.custom_indicator_id), row];
    await route.fulfill({ status: id === undefined ? 201 : 200, json: row });
  }

  await context.route(/\/api\/custom-indicators(\/\d+(\/keep)?)?$/, answerRequest);
}

test('the Settings page keeps a custom indicator of the AI assistant', async ({ page, context }) => {
  const aiRow = { custom_indicator_id: 7, key: 'custom_7', expression: FORMULA.expression, chart_placement: 'own', value_description: 'The ratio.', assistant_conversation_id: 3 };
  await useLocalCustomIndicators(context, [
    { ...aiRow, name: 'Of the AI', kept: false },
    { ...aiRow, custom_indicator_id: 8, key: 'custom_8', name: 'Of the user', kept: true, assistant_conversation_id: null },
  ]);
  await page.goto('/settings');

  const aiIndicator = page.getByRole('row', { name: /Of the AI/ });
  await expect(page.getByRole('button', { name: 'Keep Of the user' })).toHaveCount(0);
  await expect(page.getByRole('img', { name: 'Kept' })).toHaveCount(0);

  await page.getByRole('button', { name: 'Keep Of the AI' }).click();

  await expect(page.getByRole('button', { name: 'Keep Of the AI' })).toHaveCount(0);
  await expect(aiIndicator.getByRole('img', { name: 'Kept' })).toBeVisible();
  await expect(page.getByRole('row', { name: /Of the user/ }).getByRole('img', { name: 'Kept' })).toHaveCount(0);
});

test('the Settings page creates, changes, and deletes a custom indicator, and a problem shows at its field', async ({ page, context }) => {
  await useLocalCustomIndicators(context);
  await page.goto('/settings');
  await expect(page.getByText('No custom indicators')).toBeVisible();

  await page.getByRole('button', { name: 'New custom indicator' }).click();
  const dialog = page.getByRole('dialog', { name: 'New custom indicator' });
  await dialog.getByLabel('Name').fill('Close ratio');
  await dialog.getByLabel('Expression').fill('foo');
  await dialog.getByLabel('Value description').fill('The close over SMA(20).');
  await dialog.getByRole('button', { name: 'Save custom indicator' }).click();
  await expect(dialog.getByText("Column 1: Unknown name 'foo'.")).toBeVisible();

  await dialog.getByLabel('Expression').fill('close / sma(20)');
  await dialog.getByRole('button', { name: 'Save custom indicator' }).click();
  await expect(dialog).toBeHidden();
  const table = page.getByRole('region', { name: 'Custom indicators table' });
  await expect(table.getByRole('row', { name: /Close ratio/ })).toContainText('close / sma(20)');

  await page.getByRole('button', { name: 'Change Close ratio' }).click();
  const changeDialog = page.getByRole('dialog', { name: 'Change custom indicator' });
  await expect(changeDialog.getByLabel('Expression')).toHaveValue('close / sma(20)');
  await changeDialog.getByLabel('Expression').fill('close / sma(50)');
  await changeDialog.getByRole('button', { name: 'Save custom indicator' }).click();
  await expect(table.getByRole('row', { name: /Close ratio/ })).toContainText('close / sma(50)');

  await page.getByRole('button', { name: 'Delete Close ratio' }).click();
  await page.getByRole('dialog', { name: 'Delete Close ratio' }).getByRole('button', { name: 'Delete custom indicator' }).click();
  await expect(page.getByText('No custom indicators')).toBeVisible();
});

// A saved reference with the old expression, and the catalog with the new one. The screen page runs each change at once.
test('"Use current expression" gives a saved screen the changed expression, and a 422 shows until each place has it', async ({ page, context, request }, currentTest) => {
  const oldReference = { indicator: 'custom_1', parameters: {}, output: 'value', formula: FORMULA };
  const newFormula = { ...FORMULA, expression: 'close / sma(30)' };
  await context.route('**/api/screen-indicators', async (route) => {
    const response = await route.fetch();
    const custom = { ...CUSTOM_ITEM, formula: newFormula };
    await route.fulfill({ json: [...((await response.json()) as unknown[]), custom] });
  });
  const name = `Current expression ${currentTest.project.name} ${String(Date.now())}`;
  const definition = {
    start: 'watchlist',
    filters: [],
    indicator_conditions: [{ kind: 'compare', indicator: oldReference, operator: '>', value: '0' }],
    order: { indicator: oldReference, direction: 'descending' },
  };
  await page.goto(`/screens/${String(await createScreenWithRun(request, name, definition))}`);

  const useCurrent = page.getByRole('button', { name: 'Use current expression' });
  await page.getByRole('button', { name: 'Edit Close ratio descending', exact: true }).click();
  await useCurrent.click();
  await expect(useCurrent).toBeHidden();
  await page.getByRole('button', { name: 'Apply' }).click();
  const bar = page.getByRole('list', { name: 'Conditions' });
  await expect(bar.getByRole('alert')).toContainText('has 2 different references');

  await page.getByRole('button', { name: 'Edit Close ratio > 0', exact: true }).click();
  await useCurrent.click();
  const run = page.waitForRequest((sent) => sent.method() === 'POST' && sent.url().includes('/runs'));
  await page.getByRole('button', { name: 'Apply' }).click();
  expect((await run).postData()).toContain('close / sma(30)');
  await expect(bar.getByRole('alert')).toHaveCount(0);
});

test('a line whose custom indicator left the price scale stays selected', async ({ page, context, request }, currentTest) => {
  const priceFormula = { ...FORMULA, chart_placement: 'price' };
  await context.route('**/api/screen-indicators', async (route) => {
    const response = await route.fetch();
    await route.fulfill({ json: [...((await response.json()) as unknown[]), { ...CUSTOM_ITEM, formula: FORMULA }] });
  });
  const reference = { indicator: 'custom_1', parameters: {}, output: 'value', formula: priceFormula };
  const definition = {
    start: 'watchlist',
    filters: [],
    indicator_conditions: [{ kind: 'close_versus_line', indicator: reference, side: 'above' }],
    order: { indicator: { indicator: 'sma', parameters: { period: 3 }, output: 'value' }, direction: 'descending' },
  };
  const name = `Line ${currentTest.project.name} ${String(Date.now())}`;
  await page.goto(`/screens/${String(await createScreenWithRun(request, name, definition))}`);

  await page.getByRole('button', { name: 'Edit Close above Close ratio', exact: true }).click();
  await expect(page.getByRole('combobox', { name: 'Line' })).toHaveText('Close ratio');
  await expect(page.getByRole('button', { name: 'Use current expression' })).toHaveCount(0);
});

test('"Use current expression" gives a rule the changed expression', async ({ page, context }, currentTest) => {
  let formula = FORMULA;
  await context.route('**/api/market-data/indicators', async (route) => {
    const response = await route.fetch();
    await route.fulfill({ json: [...((await response.json()) as unknown[]), { ...CUSTOM_ITEM, formula }] });
  });
  await page.goto('/strategies');
  await page.getByRole('button', { name: 'New strategy' }).click();
  await page.getByLabel('Strategy name').fill(`Current rule ${currentTest.project.name} ${String(Date.now())}`);
  await page.getByRole('button', { name: 'Create strategy' }).click();
  await expect(page).toHaveURL(/\/strategies\/\d+$/);
  await page.getByRole('tablist', { name: 'Files' }).getByRole('tab', { name: 'Rules' }).click();
  await page.getByRole('button', { name: 'Add condition to Entry' }).click();
  await page.getByRole('combobox', { name: 'Entry condition 1 right side', exact: true }).click();
  await page.getByRole('option', { name: 'Close ratio' }).click();
  await page.getByRole('button', { name: 'Save rules as new version, unsaved changes' }).click();
  await expect(page.getByRole('combobox', { name: 'Version' })).toHaveText('v2');

  const strategyId = new URL(page.url()).pathname.split('/').at(-1) ?? '';
  expect(await readVersionCode(page.request, strategyId, 2)).toContain('close / sma(20)');

  formula = { ...FORMULA, expression: 'close / sma(30)' };
  await page.reload();
  await page.getByRole('tablist', { name: 'Files' }).getByRole('tab', { name: 'Rules' }).click();
  const useCurrent = page.getByRole('button', { name: 'Use current expression in Entry condition 1 right side' });
  await useCurrent.click();
  await expect(useCurrent).toBeHidden();
  await page.getByRole('button', { name: 'Save rules as new version, unsaved changes' }).click();
  await expect(page.getByRole('combobox', { name: 'Version' })).toHaveText('v3');
  expect(await readVersionCode(page.request, strategyId, 3)).toContain('close / sma(30)');
});

test('Add indicator adds a custom indicator of the catalog, and the backend calculates its values', async ({ page, context }) => {
  await useLocalChartIndicatorSet(context);
  await context.route('**/api/market-data/indicators', async (route) => {
    const response = await route.fetch();
    const catalog = (await response.json()) as unknown[];
    await route.fulfill({ json: [...catalog, { ...CUSTOM_ITEM, formula: FORMULA }] });
  });
  await page.goto(CHART_PATH);
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('1096 bars');

  await page.getByRole('button', { name: 'Add indicator' }).click();
  const dialog = page.getByRole('dialog', { name: 'Add indicator' });
  await dialog.getByRole('option', { name: 'Close ratio' }).click();

  const row = page.getByRole('list', { name: 'Legend' }).getByRole('listitem').filter({ hasText: 'Close ratio' });
  await expect(row.locator('.legend-value')).toHaveText(/^\d+\.\d{2}$/);
});

const DAYS = { name: 'days', label: 'Days', value_type: 'int', default: 20, minimum: 5, maximum: 250, description: '' };

test('the Settings page saves the parameters of a custom indicator, and a number field without a number has a problem', async ({ page, context }) => {
  await useLocalCustomIndicators(context);
  await page.goto('/settings');

  await page.getByRole('button', { name: 'New custom indicator' }).click();
  const dialog = page.getByRole('dialog', { name: 'New custom indicator' });
  await dialog.getByLabel('Name', { exact: true }).first().fill('Close ratio');
  await dialog.getByLabel('Expression').fill('width = close / mean(close, days)\nwidth - 1');
  await dialog.getByLabel('Value description').fill('The close over its mean.');
  await dialog.getByRole('button', { name: 'Add parameter' }).click();
  const parameter = dialog.getByRole('group', { name: 'Parameter 1' });
  await parameter.getByLabel('Name').fill('days');
  await parameter.getByLabel('Label').fill('Days');
  await parameter.getByLabel('Default').fill('20');
  await parameter.getByLabel('Minimum').fill('5');
  await dialog.getByRole('button', { name: 'Save custom indicator' }).click();
  await expect(parameter.getByText('Enter a number.')).toBeVisible();

  await parameter.getByLabel('Maximum').fill('250');
  const saved = page.waitForRequest((sent) => sent.method() === 'POST' && sent.url().endsWith('/api/custom-indicators'));
  await dialog.getByRole('button', { name: 'Save custom indicator' }).click();
  expect(((await saved).postDataJSON() as { parameters: unknown[] }).parameters).toEqual([DAYS]);
  await expect(dialog).toBeHidden();

  await page.getByRole('button', { name: 'Change Close ratio' }).click();
  const changeDialog = page.getByRole('dialog', { name: 'Change custom indicator' });
  await expect(changeDialog.getByLabel('Expression')).toHaveValue('width = close / mean(close, days)\nwidth - 1');
  await expect(changeDialog.getByRole('group', { name: 'Parameter 1' }).getByLabel('Maximum')).toHaveValue('250');
  await changeDialog.getByRole('button', { name: 'Remove parameter 1' }).click();
  await expect(changeDialog.getByRole('group', { name: 'Parameter 1' })).toHaveCount(0);
});

test('a chart shows 1 custom indicator 2 times with 2 parameter values, and the settings change a value', async ({ page, context }) => {
  await useLocalChartIndicatorSet(context);
  const formula = { ...FORMULA, expression: 'close / mean(close, days)', parameters: [DAYS] };
  const { description, ...catalogParameter } = DAYS;
  await context.route('**/api/market-data/indicators', async (route) => {
    const response = await route.fetch();
    const catalog = (await response.json()) as unknown[];
    await route.fulfill({ json: [...catalog, { ...CUSTOM_ITEM, parameters: [{ ...catalogParameter, description, is_in_name: true }], formula }] });
  });
  await page.goto(CHART_PATH);
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('1096 bars');

  for (const _ of [1, 2]) {
    await page.getByRole('button', { name: 'Add indicator' }).click();
    await page.getByRole('dialog', { name: 'Add indicator' }).getByRole('option', { name: 'Close ratio' }).click();
  }
  const legend = page.getByRole('list', { name: 'Legend' });
  await expect(legend.getByRole('listitem').filter({ hasText: 'Close ratio 20' })).toHaveCount(2);

  const first = legend.getByRole('listitem').filter({ hasText: 'Close ratio 20' }).first();
  await first.locator('.legend-name').hover();
  await first.getByRole('button', { name: 'Settings for Close ratio 20' }).click();
  const settings = page.getByRole('dialog', { name: 'Close ratio' });
  await settings.getByRole('spinbutton', { name: 'Days' }).fill('60');
  await settings.getByRole('button', { name: 'Apply' }).click();

  for (const name of ['Close ratio 60', 'Close ratio 20']) {
    const row = legend.getByRole('listitem').filter({ hasText: name });
    await expect(row).toHaveCount(1);
    await expect(row.locator('.legend-value')).toHaveText(/^\d+\.\d{2}$/);
  }
});
