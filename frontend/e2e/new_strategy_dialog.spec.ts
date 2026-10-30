// "New strategy" dialog (#176, docs/architecture/strategy.md section 9.7.1): the start point list, the rows of the
// selected template, and a strategy made from template S1. The e2e database is not cleared between tests and browser
// projects, so each strategy name is unique.
import { expect, test } from '@playwright/test';

const TEMPLATE_ROW_LABELS = ['Entry', 'Exit', 'Defaults', 'Market', 'Bar period', 'Evidence', 'Sources', 'Differs from source'];

test('the dialog lists the start points and shows the rows of the selected template', async ({ page }) => {
  await page.goto('/strategies');
  await page.getByRole('button', { name: 'New strategy' }).click();
  const dialog = page.getByRole('dialog', { name: 'New strategy' });
  const startPoints = dialog.getByRole('listbox', { name: 'Start from' });

  await expect(startPoints.getByRole('option')).toHaveText([
    'Blank code',
    'Blank rules',
    '200-day trend',
    '50-day range break',
    '12-month time-series momentum',
  ]);
  await expect(startPoints.getByRole('option', { name: 'Blank code' })).toHaveAttribute('aria-selected', 'true');
  await expect(dialog.getByRole('heading', { level: 3 })).toHaveText('Blank code');
  await expect(dialog.locator('dt')).toHaveCount(0);

  await startPoints.getByRole('option', { name: '200-day trend' }).click();

  await expect(dialog.getByRole('heading', { level: 3 })).toHaveText('200-day trend');
  await expect(dialog.locator('dt')).toHaveText(TEMPLATE_ROW_LABELS);
  await expect(dialog.getByRole('link', { name: 'Brock, Lakonishok & LeBaron 1992' })).toHaveAttribute(
    'href',
    'https://doi.org/10.1111/j.1540-6261.1992.tb04681.x',
  );
  await expect(dialog.getByRole('link')).toHaveCount(2);
});

test('a strategy from template S1 opens with version 1 made by the rule builder', async ({ page }, testInfo) => {
  const name = `S1 trend ${testInfo.project.name} ${String(Date.now())}`;
  await page.goto('/strategies');
  await page.getByRole('button', { name: 'New strategy' }).click();
  const dialog = page.getByRole('dialog', { name: 'New strategy' });
  await dialog.getByLabel('Strategy name').fill(name);
  await dialog.getByRole('listbox', { name: 'Start from' }).getByRole('option', { name: '200-day trend' }).click();

  const request = page.waitForRequest((sent) => sent.method() === 'POST' && sent.url().endsWith('/api/strategies'));
  await dialog.getByRole('button', { name: 'Create strategy' }).click();

  expect((await request).postDataJSON()).toEqual({ name, start_from: 's1' });
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(name);
  await expect(page.getByRole('textbox', { name: 'Strategy code' })).toContainText('200-day trend');
  const strategyId = /\/strategies\/(\d+)/.exec(page.url())?.[1];
  const version = await page.request.get(`/api/strategies/${String(strategyId)}/versions/1`);
  expect(await version.json()).toMatchObject({ version_number: 1, source: 'rule_builder' });
});
