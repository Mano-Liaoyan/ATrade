// Custom indicators (docs/architecture/indicator.md section 23.10). The Playwright projects run at the same time against
// one database, and other tests count the catalog, so these tests keep the custom indicators in the browser context. The
// series route is the real backend.
import { expect, test, type BrowserContext, type Route } from '@playwright/test';
import { useLocalChartIndicatorSet } from './local_chart_indicator_set';

const CHART_PATH = '/instruments/SEHK/700?currency=HKD&bar_period=1-DAY';
const FORMULA = { name: 'Close ratio', expression: 'close / sma(20)', chart_placement: 'own' };

interface Row {
  custom_indicator_id: number;
  key: string;
  name: string;
  expression: string;
  chart_placement: string;
  value_description: string;
}

async function useLocalCustomIndicators(context: BrowserContext): Promise<void> {
  let rows: Row[] = [];
  let nextId = 1;

  async function answerRequest(route: Route): Promise<void> {
    const request = route.request();
    const id = /\/(\d+)$/.exec(new URL(request.url()).pathname)?.[1];
    if (request.method() === 'GET') {
      await route.fulfill({ json: rows });
      return;
    }
    if (request.method() === 'DELETE') {
      rows = rows.filter((row) => String(row.custom_indicator_id) !== id);
      await route.fulfill({ status: 204 });
      return;
    }
    const fields = request.postDataJSON() as Omit<Row, 'custom_indicator_id' | 'key'>;
    if (fields.expression === 'foo') {
      const problem = { location: ['expression'], message: "Column 1: Unknown name 'foo'." };
      await route.fulfill({ status: 422, json: { problems: [problem] } });
      return;
    }
    const row = { ...fields, custom_indicator_id: id === undefined ? nextId : Number(id), key: `custom_${id ?? String(nextId)}` };
    nextId += 1;
    rows = [...rows.filter((item) => item.custom_indicator_id !== row.custom_indicator_id), row];
    await route.fulfill({ status: id === undefined ? 201 : 200, json: row });
  }

  await context.route(/\/api\/custom-indicators(\/\d+)?$/, answerRequest);
}

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

test('Add indicator adds a custom indicator of the catalog, and the backend calculates its values', async ({ page, context }) => {
  await useLocalChartIndicatorSet(context);
  await context.route('**/api/market-data/indicators', async (route) => {
    const response = await route.fetch();
    const catalog = (await response.json()) as unknown[];
    const custom = {
      key: 'custom_1',
      name: FORMULA.name,
      short_name: FORMULA.name,
      chart_placement: 'own',
      parameters: [],
      outputs: ['value'],
      value_description: 'The close over SMA(20).',
      formula: FORMULA,
    };
    await route.fulfill({ json: [...catalog, custom] });
  });
  await page.goto(CHART_PATH);
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('1096 bars');

  await page.getByRole('button', { name: 'Add indicator' }).click();
  const dialog = page.getByRole('dialog', { name: 'Add indicator' });
  await dialog.getByRole('option', { name: 'Close ratio' }).click();

  const row = page.getByRole('list', { name: 'Legend' }).getByRole('listitem').filter({ hasText: 'Close ratio' });
  await expect(row.locator('.legend-value')).toHaveText(/^\d+\.\d{2}$/);
});
