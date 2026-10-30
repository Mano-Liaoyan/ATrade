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
  // The editor draws only the lines in view. The first lines name the config class of the made code.
  await expect(code).toContainText('class RulesConfig(StrategyConfig)');
  await expect(page.locator('.code-editor__highlighted-line')).toHaveCount(0);
  const pageScrollY = await page.evaluate(() => window.scrollY);

  await page.getByRole('button', { name: 'Add condition to Entry' }).click();
  await expect(page.locator('.code-editor__highlighted-line').first()).toBeInViewport();
  // The first changed line is near the top: an indicator adds its import and the warm-up bar count.
  await expect(code).toContainText('import atrade.indicator');

  await page.getByRole('spinbutton', { name: 'Entry condition 1 right side SMA period' }).fill('20');
  await expect(code).toContainText('WARM_UP_BAR_COUNT = 20');
  await expect(page.locator('.code-editor__highlighted-line').first()).toBeInViewport();
  expect(await page.evaluate(() => window.scrollY)).toBe(pageScrollY);

  await page.getByRole('button', { name: 'Save rules as new version, unsaved changes' }).click();
  await expect(page.getByRole('combobox', { name: 'Version' })).toHaveText('v2');
  const strategyId = new URL(page.url()).pathname.split('/').at(-1) ?? '';
  const strategy = (await (await page.request.get(`/api/strategies/${strategyId}`)).json()) as {
    versions: { version_number: number; source: string }[];
  };
  expect(strategy.versions.at(-1)).toMatchObject({ version_number: 2, source: 'rule_builder' });
  const version = (await (await page.request.get(`/api/strategies/${strategyId}/versions/2`)).json()) as { code: string };
  expect(version.code).toContain('class RulesStrategy');
  expect(version.code).toContain('sma_1_period: int = 20');
  await expect(page.getByRole('spinbutton', { name: 'Entry condition 1 right side SMA period' })).toHaveValue('20');
});

interface StrategyBody {
  id: number;
  versions: { version_number: number; source: string }[];
}

// Version 1 is the blank code. Rules saved as v2, then code saved as v3 (section 9.8.4).
async function createStrategyWithCodeAfterRules(page: Page, name: string): Promise<number> {
  // eslint-disable-next-line @typescript-eslint/naming-convention -- `data` is the request body option of Playwright.
  const created = (await (await page.request.post('/api/strategies', { data: { name } })).json()) as StrategyBody;
  const rules = {
    format_version: 1,
    settings: { position_size: { type: 'fixed_shares', shares: 7 } },
    entry: { type: 'group', match: 'all_of', items: [] },
    exits: { exit_when_entry_is_false: false },
  };
  const versionsUrl = `/api/strategies/${String(created.id)}/versions`;
  // eslint-disable-next-line @typescript-eslint/naming-convention -- `data` is the request body option of Playwright.
  const rulesVersion = await page.request.post(versionsUrl, { data: { rules } });
  expect(rulesVersion.status()).toBe(201);
  const { code } = (await rulesVersion.json()) as { code: string };
  // eslint-disable-next-line @typescript-eslint/naming-convention -- `data` is the request body option of Playwright.
  const codeVersion = await page.request.post(versionsUrl, { data: { code: `${code}\n# Changed by hand.\n` } });
  expect(codeVersion.status()).toBe(201);
  return created.id;
}

async function readVersions(page: Page, strategyId: number): Promise<StrategyBody['versions']> {
  const strategy = (await (await page.request.get(`/api/strategies/${String(strategyId)}`)).json()) as StrategyBody;
  return strategy.versions;
}

test('the Rules tab warns when the code changed after the rules and shows the diff before the save', async ({
  page,
}, currentTest) => {
  const strategyId = await createStrategyWithCodeAfterRules(page, createUniqueName(currentTest, 'Warning'));
  await page.goto(`/strategies/${String(strategyId)}`);
  await expect(page.getByRole('combobox', { name: 'Version' })).toHaveText('v3');
  await page.getByRole('tablist', { name: 'Files' }).getByRole('tab', { name: 'Rules' }).click();

  await expect(page.getByRole('alert')).toHaveText('Code of v3 changed. Rules are from v2.');
  await expect(page.getByRole('spinbutton', { name: 'Shares per trade' })).toHaveValue('7');

  const save = page.getByRole('button', { name: 'Save rules as new version' });
  await save.click();
  const dialog = page.getByRole('dialog', { name: 'Replace code changes of v3' });
  await expect(dialog.getByRole('region', { name: 'Code difference' })).toBeVisible();
  await expect(dialog).toContainText('# Changed by hand.');
  await dialog.getByRole('button', { name: 'Cancel' }).click();
  await expect(dialog).toBeHidden();
  expect(await readVersions(page, strategyId)).toHaveLength(3);

  await save.click();
  await dialog.getByRole('button', { name: 'Save rules as new version' }).click();
  await expect(page.getByRole('combobox', { name: 'Version' })).toHaveText('v4');
  expect((await readVersions(page, strategyId)).at(-1)).toMatchObject({ version_number: 4, source: 'rule_builder' });
  await expect(page.getByRole('alert')).toHaveCount(0);
});

test('the Rules tab of a version with rules has no warning and saves without a diff', async ({ page }, currentTest) => {
  const strategyId = await createStrategyWithCodeAfterRules(page, createUniqueName(currentTest, 'No warning'));
  await page.goto(`/strategies/${String(strategyId)}/versions/2`);
  await expect(page.getByRole('combobox', { name: 'Version' })).toHaveText('v2');
  await page.getByRole('tablist', { name: 'Files' }).getByRole('tab', { name: 'Rules' }).click();
  const shares = page.getByRole('spinbutton', { name: 'Shares per trade' });
  await expect(shares).toHaveValue('7');
  await expect(page.getByRole('alert')).toHaveCount(0);

  await shares.fill('8');
  await page.getByRole('button', { name: 'Save rules as new version, unsaved changes' }).click();
  await expect(page.getByRole('combobox', { name: 'Version' })).toHaveText('v4');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  expect((await readVersions(page, strategyId)).at(-1)).toMatchObject({ version_number: 4, source: 'rule_builder' });
});

test('the Rules tab shows the universe mode settings and makes multi-instrument code', async ({
  page,
}, currentTest) => {
  const name = createUniqueName(currentTest, 'Universe rules');
  // eslint-disable-next-line @typescript-eslint/naming-convention -- `data` is the request body option of Playwright.
  const created = (await (await page.request.post('/api/strategies', { data: { name } })).json()) as StrategyBody;
  const rules = {
    format_version: 1,
    settings: {
      position_size: { type: 'percent_of_equity', percent: 95 },
      universe: {
        rank_indicator: { type: 'indicator', indicator: 'momentum_12_1', parameters: {} },
        rank_direction: 'high_to_low',
        hold_count: 2,
        rebalance_period: 'monthly',
      },
    },
    entry: { type: 'group', match: 'all_of', items: [] },
    exits: { exit_when_entry_is_false: false },
  };
  const versionsUrl = `/api/strategies/${String(created.id)}/versions`;
  // eslint-disable-next-line @typescript-eslint/naming-convention -- `data` is the request body option of Playwright.
  expect((await page.request.post(versionsUrl, { data: { rules } })).status()).toBe(201);

  await page.goto(`/strategies/${String(created.id)}`);
  await page.getByRole('tablist', { name: 'Files' }).getByRole('tab', { name: 'Rules' }).click();
  const code = page.getByRole('region', { name: 'Code from the rules' });
  await expect(page.getByRole('heading', { name: 'Entry filter' })).toBeVisible();
  await expect(page.getByText('Position size')).toHaveCount(0);
  // The editor draws only the lines in view. The first line names the universe mode.
  await expect(code).toContainText('Strategy from the rule builder in the universe mode');

  await page.getByRole('spinbutton', { name: 'Hold' }).fill('3');
  await expect(code).toContainText('hold_count: int = 3');
});
