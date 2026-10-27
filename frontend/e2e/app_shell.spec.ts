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

test('the header navigation marks the current page', async ({ page }) => {
  await page.goto('/backtests');
  const navigation = page.getByRole('banner').getByRole('navigation');

  await expect(navigation.getByRole('link', { name: 'Backtests' })).toHaveAttribute('aria-current', 'page');
  await expect(navigation.getByRole('link', { name: 'Home' })).not.toHaveAttribute('aria-current');

  await navigation.getByRole('link', { name: 'Strategies' }).click();

  await expect(navigation.getByRole('link', { name: 'Strategies' })).toHaveAttribute('aria-current', 'page');
  await expect(navigation.getByRole('link', { name: 'Backtests' })).not.toHaveAttribute('aria-current');
});

// The header is a Carbon g100 zone in the light and in the dark theme: background #161616.
for (const colorScheme of ['light', 'dark'] as const) {
  test(`the header is dark in the ${colorScheme} system theme`, async ({ page }) => {
    await page.emulateMedia({ colorScheme });
    await page.goto('/');

    await expect(page.getByRole('banner')).toHaveCSS('background-color', 'rgb(22, 22, 22)');
  });
}

// The page uses Carbon g10 in the light system theme (background #f4f4f4) and g100 in the dark one (#161616).
test('the page background follows the system theme', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'light' });
  await page.goto('/');
  await expect(page.locator('body')).toHaveCSS('background-color', 'rgb(244, 244, 244)');

  await page.emulateMedia({ colorScheme: 'dark' });

  await expect(page.locator('body')).toHaveCSS('background-color', 'rgb(22, 22, 22)');
});

test('the Paper tag shows the masked paper account on hover and on keyboard focus', async ({ page }) => {
  await page.goto('/');
  const paperTag = page.getByRole('banner').getByText('Paper', { exact: true });
  await expect(paperTag).toBeVisible();

  await paperTag.hover();
  await expect(page.getByRole('tooltip')).toHaveText('Paper account DU****567');

  await page.mouse.move(400, 400);
  await expect(page.getByRole('tooltip')).toBeHidden();

  await page.getByRole('banner').getByRole('button', { name: 'Paper' }).focus();
  await expect(page.getByRole('tooltip')).toHaveText('Paper account DU****567');
});

// ATrade serves the IBM Plex fonts from its own build. The fonts load when no other host can be reached.
test('the page text uses IBM Plex fonts from the ATrade build', async ({ page }) => {
  const appHost = new URL(test.info().project.use.baseURL ?? '').host;
  await page.route(
    (url) => url.host !== appHost,
    (route) => route.abort(),
  );
  await page.goto('/');

  await expect(page.locator('body')).toHaveCSS('font-family', /^"?IBM Plex Sans"?,/);
  const loadedFamilies = await page.evaluate(async () => {
    await document.fonts.load('16px "IBM Plex Sans"');
    await document.fonts.load('16px "IBM Plex Mono"');
    return [...document.fonts].filter((face) => face.status === 'loaded').map((face) => face.family.replaceAll('"', ''));
  });
  expect(loadedFamilies).toContain('IBM Plex Sans');
  expect(loadedFamilies).toContain('IBM Plex Mono');
});
