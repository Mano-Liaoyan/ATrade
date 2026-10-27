// The account panel with the IBKR fake of backend/tests/e2e_server.py: account DU1234567, a balance, and 40 positions.
import { expect, test } from '@playwright/test';

test('account panel shows the checked paper account and its balance', async ({ page }) => {
  await page.goto('/');

  await expect(page.getByRole('status', { name: 'Paper account check' })).toHaveText('Paper account DU1234567 checked.');
  const balance = page.getByRole('definition');
  await expect(balance.first()).toHaveText('101,234.50');
  await expect(balance.nth(1)).toHaveText('25,000.00');
  await expect(page.getByRole('note', { name: 'Balance currency' })).toHaveText('Base currency USD.');
});

test('position table has a visible scroll track and its last row can be scrolled into view', async ({ page }) => {
  await page.goto('/');
  const positions = page.getByRole('region', { name: 'Positions' });
  const lastRow = positions.getByRole('row', { name: /TEST40/ });
  const track = page.getByRole('scrollbar', { name: 'Positions scroll bar' });
  const thumb = track.locator('.scroll-thumb');
  // Other parts of the home page can push the panel below the window.
  await positions.scrollIntoViewIfNeeded();

  await expect(positions.getByRole('row', { name: /TEST01/ })).toBeInViewport();
  await expect(track).toBeVisible();
  await expect(thumb).toBeVisible();
  await expect(lastRow).not.toBeInViewport();

  await track.focus();
  await page.keyboard.press('End');

  await expect(lastRow).toBeInViewport();
  await expect(thumb).toBeVisible();
  await expect(track).toHaveAttribute('aria-valuenow', '100');
});
