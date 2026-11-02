// Live updates without a reload: a change from another client (here the API) shows at once, because the change
// socket of the list pushes it (docs/architecture.md section 13 "Live updates"). The context menu of a list row
// deletes the row after the danger dialog.
import { expect, test, type APIRequestContext } from '@playwright/test';

async function createStrategy(request: APIRequestContext, name: string): Promise<number> {
  // eslint-disable-next-line @typescript-eslint/naming-convention -- `data` is the request body option of Playwright.
  const response = await request.post('/api/strategies', { data: { name } });
  expect(response.status()).toBe(201);
  return ((await response.json()) as { id: number }).id;
}

test('the strategy list shows a strategy that another client creates and deletes, without a reload', async ({ page, request }, currentTest) => {
  const name = `Live ${currentTest.project.name} ${String(Date.now())}`;
  await page.goto('/strategies');
  const list = page.getByRole('complementary', { name: 'Strategies' });
  await expect(list.getByRole('table')).toBeVisible();

  const strategyId = await createStrategy(request, name);
  await expect(list.getByRole('link', { name, exact: true })).toBeVisible();

  expect((await request.delete(`/api/strategies/${String(strategyId)}`)).ok()).toBe(true);
  await expect(list.getByRole('link', { name, exact: true })).toHaveCount(0);
});

test('the context menu of a strategy row deletes the strategy after the danger dialog', async ({ page, request }, currentTest) => {
  const name = `Menu ${currentTest.project.name} ${String(Date.now())}`;
  const strategyId = await createStrategy(request, name);
  await page.goto('/strategies');
  const list = page.getByRole('complementary', { name: 'Strategies' });
  const link = list.getByRole('link', { name, exact: true });

  await link.click({ button: 'right' });
  const menu = page.getByRole('menu', { name });
  await expect(menu.getByRole('menuitem')).toHaveText(['Open in new tab', 'Delete strategy']);
  await menu.getByRole('menuitem', { name: 'Delete strategy' }).click();
  await expect(menu).toHaveCount(0);
  const dialog = page.getByRole('dialog', { name: `Delete ${name}` });
  await dialog.getByRole('button', { name: 'Delete strategy', exact: true }).click();

  await expect(link).toHaveCount(0);
  expect((await request.get(`/api/strategies/${String(strategyId)}`)).status()).toBe(404);
});

test('a right-click outside a row opens no menu', async ({ page }) => {
  await page.goto('/strategies');
  const list = page.getByRole('complementary', { name: 'Strategies' });
  await expect(list.getByRole('table')).toBeVisible();

  await list.getByRole('columnheader', { name: 'Strategy' }).click({ button: 'right' });

  await expect(page.getByRole('menu')).toHaveCount(0);
});
