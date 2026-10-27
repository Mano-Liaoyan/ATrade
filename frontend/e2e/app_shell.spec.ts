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

// The theme button changes the choice in the order System, Light, Dark, System. The icon shows the choice.
test('the theme button changes the theme from System to Light to Dark and back to System', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'dark' });
  await page.goto('/');
  const header = page.getByRole('banner');
  const body = page.locator('body');

  const systemButton = header.getByRole('button', { name: 'Theme: System' });
  await expect(systemButton).toBeVisible();
  const systemIcon = await systemButton.locator('svg').innerHTML();
  await expect(body).toHaveCSS('background-color', 'rgb(22, 22, 22)');

  await systemButton.click();
  // Light is Carbon g10 although the system is dark.
  const lightButton = header.getByRole('button', { name: 'Theme: Light' });
  await expect(lightButton).toBeVisible();
  await expect(body).toHaveCSS('background-color', 'rgb(244, 244, 244)');
  const lightIcon = await lightButton.locator('svg').innerHTML();
  expect(lightIcon).not.toBe(systemIcon);

  await lightButton.click();
  const darkButton = header.getByRole('button', { name: 'Theme: Dark' });
  await expect(darkButton).toBeVisible();
  await expect(body).toHaveCSS('background-color', 'rgb(22, 22, 22)');
  const darkIcon = await darkButton.locator('svg').innerHTML();
  expect(darkIcon).not.toBe(systemIcon);
  expect(darkIcon).not.toBe(lightIcon);

  await darkButton.click();
  const systemButtonAgain = header.getByRole('button', { name: 'Theme: System' });
  await expect(systemButtonAgain).toBeVisible();
  expect(await systemButtonAgain.locator('svg').innerHTML()).toBe(systemIcon);
});

test('the theme button shows its choice in a tooltip', async ({ page }) => {
  await page.goto('/');

  await page.getByRole('banner').getByRole('button', { name: 'Theme: System' }).hover();

  await expect(page.getByRole('tooltip')).toHaveText('Theme: System');
});

test('the theme choice stays after a page reload', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'light' });
  await page.goto('/');
  const header = page.getByRole('banner');
  await header.getByRole('button', { name: 'Theme: System' }).click();
  await header.getByRole('button', { name: 'Theme: Light' }).click();
  // Dark is Carbon g100 although the system is light.
  await expect(page.locator('body')).toHaveCSS('background-color', 'rgb(22, 22, 22)');

  await page.reload();

  await expect(header.getByRole('button', { name: 'Theme: Dark' })).toBeVisible();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await expect(page.locator('body')).toHaveCSS('background-color', 'rgb(22, 22, 22)');
});

test('the theme button works when the browser storage is not available', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(window, 'localStorage', {
      get() {
        throw new DOMException('The storage is not available.', 'SecurityError');
      },
    });
  });
  await page.emulateMedia({ colorScheme: 'light' });
  await page.goto('/');
  const header = page.getByRole('banner');

  await header.getByRole('button', { name: 'Theme: System' }).click();
  await header.getByRole('button', { name: 'Theme: Light' }).click();

  await expect(header.getByRole('button', { name: 'Theme: Dark' })).toBeVisible();
  await expect(page.locator('body')).toHaveCSS('background-color', 'rgb(22, 22, 22)');
});
