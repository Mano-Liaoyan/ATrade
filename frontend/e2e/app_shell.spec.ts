// Opens the app shell that the backend serves, in each browser project.
import { expect, test, type Page } from '@playwright/test';

// The browser clock stands still until a test moves it, so the server time in the header does not change by itself.
async function stopBrowserClock(page: Page): Promise<void> {
  await page.clock.install({ time: new Date('2026-06-01T00:00:00Z') });
  await page.clock.pauseAt(new Date('2026-06-01T00:00:01Z'));
}

test('app shell shows the product name and a connected backend', async ({ page }) => {
  await stopBrowserClock(page);
  await page.goto('/');

  await expect(page.getByRole('banner')).toContainText('ATrade');
  await expect(page.getByRole('status', { name: 'Backend status' })).toHaveText('Backend connected. Server time 2026-01-02 03:04:05 UTC.');
});

test('the server time in the header ticks after the page load', async ({ page }) => {
  await stopBrowserClock(page);
  await page.goto('/');
  const backendStatus = page.getByRole('status', { name: 'Backend status' });
  await expect(backendStatus).toHaveText('Backend connected. Server time 2026-01-02 03:04:05 UTC.');

  await page.clock.runFor(62_000);

  await expect(backendStatus).toHaveText('Backend connected. Server time 2026-01-02 03:05:07 UTC.');
});

test('app shell loads for a page path that the backend does not know', async ({ page }) => {
  await page.goto('/no/such/page');

  await expect(page.getByRole('banner')).toContainText('ATrade');
});

test('app shell shows that IB Gateway is connected', async ({ page }) => {
  await page.goto('/');

  await expect(page.getByRole('status', { name: 'IB Gateway status' })).toHaveText('IB Gateway connected.');
});
