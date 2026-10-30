// Discarded strategy versions (#180, docs/architecture/assistant.md 25.5.3). backend/tests/e2e_server.py adds the
// strategy "E2E discarded version": v1 of the user, v2 of the AI assistant with the discarded mark and a failed
// backtest, and v3 of the AI assistant. The tests only read, so the browser projects can share the strategy.
import { expect, test } from '@playwright/test';

const STRATEGY_NAME = 'E2E discarded version';

test('hides the discarded version until "Show discarded versions" is on, and tags it "Discarded"', async ({ page, request }) => {
  const strategies = (await (await request.get('/api/strategies')).json()) as { id: number; name: string }[];
  const strategy = strategies.find((item) => item.name === STRATEGY_NAME);
  expect(strategy).toBeDefined();
  await page.goto(`/strategies/${String(strategy?.id)}`);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(STRATEGY_NAME);
  const versionSelect = page.getByRole('combobox', { name: 'Version' });
  // The latest version that is not discarded opens.
  await expect(versionSelect).toHaveText('v3');

  await versionSelect.click();
  await expect(page.getByRole('option')).toHaveText(['v1', 'v3']);
  await page.keyboard.press('Escape');

  const toggle = page.getByRole('switch', { name: 'Show discarded versions' });
  await expect(toggle).toHaveAttribute('aria-checked', 'false');
  // A click on the visible label changes the switch, like a click on the switch itself.
  await page.locator('label').filter({ hasText: 'Show discarded versions' }).click();
  await expect(toggle).toHaveAttribute('aria-checked', 'true');
  await versionSelect.click();
  await expect(page.getByRole('option')).toHaveText(['v1', 'v2 Discarded', 'v3']);
  await page.getByRole('option', { name: /^v2/ }).click();
  await expect(versionSelect).toHaveText('v2 Discarded');
  await expect(versionSelect.getByText('Discarded', { exact: true })).toBeVisible();
});

test('the backtest list shows the backtest of a discarded version as usual', async ({ page }) => {
  await page.goto('/backtests');
  const list = page.getByRole('complementary', { name: 'Backtests' });
  await expect(list.getByText(`${STRATEGY_NAME} v2`, { exact: true })).toHaveCount(1);
});
