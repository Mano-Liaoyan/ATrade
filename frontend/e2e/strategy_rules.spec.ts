// Rule builder: the "Rules" tab makes the code from the rules, highlights the changed lines in the code region only,
// and saves the rules as a new version (docs/architecture/strategy.md section 9.8.5).
import { expect, test, type Page, type TestInfo } from '@playwright/test';

function createUniqueName(currentTest: TestInfo, title: string): string {
  return `${title} ${currentTest.project.name} ${String(Date.now())}`;
}

async function createStrategy(page: Page, name: string): Promise<void> {
  await page.goto('/strategies');
  await page.getByRole('button', { name: 'New strategy' }).click();
  await page.getByLabel('Strategy name').fill(name);
  await page.getByRole('button', { name: 'Create strategy' }).click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(name);
}

test('the Rules tab makes code from the rules and saves them as a new version', async ({ page }, currentTest) => {
  await createStrategy(page, createUniqueName(currentTest, 'Rules'));
  const files = page.getByRole('tablist', { name: 'Files' });
  await expect(files.getByRole('tab')).toHaveText(['Rules', 'strategy.py']);

  await files.getByRole('tab', { name: 'Rules' }).click();
  const code = page.getByRole('region', { name: 'Code from the rules' });
  await expect(code).toContainText('class RulesStrategy');
  await expect(page.locator('.code-editor__highlighted-line')).toHaveCount(0);
  const pageScrollY = await page.evaluate(() => window.scrollY);

  await page.getByRole('button', { name: 'Add condition to Entry' }).click();
  await expect(page.locator('.code-editor__highlighted-line').first()).toBeInViewport();
  await expect(code).toContainText('sma_1');

  await page.getByRole('spinbutton', { name: 'Entry condition 1 right side SMA period' }).fill('20');
  await expect(code).toContainText('sma_1_period: int = 20');
  await expect(page.locator('.code-editor__highlighted-line').first()).toBeInViewport();
  expect(await page.evaluate(() => window.scrollY)).toBe(pageScrollY);

  await page.getByRole('button', { name: 'Save rules as new version, unsaved changes' }).click();
  await expect(page.getByRole('combobox', { name: 'Version' })).toHaveText('v2');
  const strategyId = new URL(page.url()).pathname.split('/').at(-1) ?? '';
  const strategy = (await (await page.request.get(`/api/strategies/${strategyId}`)).json()) as {
    versions: { version_number: number; source: string }[];
  };
  expect(strategy.versions.at(-1)).toMatchObject({ version_number: 2, source: 'rule_builder' });
  await expect(page.getByRole('spinbutton', { name: 'Entry condition 1 right side SMA period' })).toHaveValue('20');
});
