// Opens the app shell that the backend serves, in each browser project.
import { expect, test } from '@playwright/test';

test('app shell shows the product name and a connected backend', async ({ page }) => {
  await page.goto('/');

  await expect(page.getByRole('banner')).toContainText('ATrade');
  await expect(page.getByRole('status', { name: 'Backend status' })).toHaveText('Backend connected. Server time 2026-01-02 03:04:05 UTC.');
});

test('app shell loads for a page path that the backend does not know', async ({ page }) => {
  await page.goto('/no/such/page');

  await expect(page.getByRole('banner')).toContainText('ATrade');
});

test('app shell shows that IB Gateway is connected', async ({ page }) => {
  await page.goto('/');

  await expect(page.getByRole('status', { name: 'IB Gateway status' })).toHaveText('IB Gateway connected.');
});
