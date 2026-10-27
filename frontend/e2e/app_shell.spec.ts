// Opens the app shell that the backend serves, in each browser project.
import { expect, test, type Locator, type Page } from '@playwright/test';

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

// A user points at the button first, so the tooltip is open at the click. The open tooltip must not take the click.
test('the theme button changes the theme while its tooltip is open', async ({ page }) => {
  await page.goto('/');
  const header = page.getByRole('banner');

  await header.getByRole('button', { name: 'Theme: System' }).hover();
  await expect(page.getByRole('tooltip')).toHaveText('Theme: System');
  await header.getByRole('button', { name: 'Theme: System' }).click();

  await expect(header.getByRole('button', { name: 'Theme: Light' })).toBeVisible();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
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

async function openCommandPaletteWithKeys(page: Page): Promise<Locator> {
  // The palette listens for the keys after the app starts: the header button shows that the app runs.
  await expect(page.getByRole('banner').getByRole('button', { name: 'Open command palette' })).toBeVisible();
  await page.keyboard.press('ControlOrMeta+k');
  const palette = page.getByRole('dialog', { name: 'Command palette' });
  await expect(palette).toBeVisible();
  // The palette reads the watchlist when it opens, and the list is aria-busy until the read ends. Watchlist commands
  // that arrive later move the highlight to the first command (Bits UI Command sorts again), so wait for the read.
  await expect(palette.getByRole('listbox')).toHaveAttribute('aria-busy', 'false');
  return palette;
}

test('the command palette opens and closes with Ctrl K or Cmd K, with Escape, and with the header button', async ({
  page,
}) => {
  await page.goto('/');
  const palette = await openCommandPaletteWithKeys(page);
  await expect(palette.getByRole('combobox')).toBeFocused();

  await page.keyboard.press('ControlOrMeta+k');
  await expect(palette).toBeHidden();

  await page.getByRole('banner').getByRole('button', { name: 'Open command palette' }).click();
  await expect(palette).toBeVisible();

  await page.keyboard.press('Escape');
  await expect(palette).toBeHidden();
});

test('the command palette filters the commands and runs the highlighted command with Enter', async ({ page }) => {
  await page.goto('/');
  const palette = await openCommandPaletteWithKeys(page);
  const commandText = palette.getByRole('combobox');

  await commandText.fill('Go to');
  const highlighted = palette.getByRole('option', { selected: true });
  await expect(highlighted).toHaveCount(1);
  const firstName = (await highlighted.textContent()) ?? '';
  await page.keyboard.press('ArrowDown');
  await expect(highlighted).not.toHaveText(firstName);
  await page.keyboard.press('ArrowUp');
  await expect(highlighted).toHaveText(firstName);

  await commandText.fill('zzzz');
  await expect(palette.getByRole('option')).toHaveCount(0);
  await expect(palette.getByText('No results', { exact: true })).toBeVisible();

  await commandText.fill('strategies');
  await expect(palette.getByRole('option')).toHaveText(['Go to Strategies']);
  await page.keyboard.press('Enter');

  await expect(palette).toBeHidden();
  await expect(page).toHaveURL('/strategies');
});

test('the command palette goes to each page and has no command that sends an order or starts a test', async ({
  page,
}) => {
  await page.goto('/strategies');
  const palette = await openCommandPaletteWithKeys(page);
  const commandNames = await palette.getByRole('option').allTextContents();
  expect(commandNames).toEqual(
    expect.arrayContaining(['Go to Home', 'Go to Strategies', 'Go to Backtests', 'Go to Forward tests']),
  );
  expect(commandNames.filter((name) => /send|start|stop|order/i.test(name))).toEqual([]);

  await palette.getByRole('option', { name: 'Go to Forward tests' }).click();

  await expect(palette).toBeHidden();
  await expect(page).toHaveURL('/forward-tests');
});

test('the command palette opens the instrument page of a watchlist instrument', async ({ page, request }) => {
  // The browser projects share one database: another project can add AAPL first (409).
  // eslint-disable-next-line @typescript-eslint/naming-convention -- `data` is the request body option of Playwright.
  const addResponse = await request.post('/api/watchlist', { data: { symbol: 'AAPL', exchange: 'NASDAQ', currency: 'USD' } });
  expect([201, 409]).toContain(addResponse.status());
  await page.goto('/strategies');
  const palette = await openCommandPaletteWithKeys(page);

  await palette.getByRole('combobox').fill('AAPL');
  await palette.getByRole('option', { name: 'AAPL / NASDAQ / USD' }).click();

  await expect(page).toHaveURL('/instruments/NASDAQ/AAPL?currency=USD');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('AAPL / NASDAQ / USD');
});

test('the command palette opens the backtest form and the forward test form', async ({ page }) => {
  await page.goto('/');
  let palette = await openCommandPaletteWithKeys(page);
  await palette.getByRole('option', { name: 'Open the backtest form' }).click();

  await expect(page).toHaveURL('/backtests#start-backtest');
  await expect(page.getByRole('form', { name: 'Start a backtest' }).locator(':focus')).toHaveCount(1);

  palette = await openCommandPaletteWithKeys(page);
  await palette.getByRole('option', { name: 'Open the forward test form' }).click();

  await expect(page).toHaveURL('/forward-tests#start-forward-test');
  await expect(page.getByRole('form', { name: 'Start a forward test' }).locator(':focus')).toHaveCount(1);
});

test('the command palette changes the theme, and the theme button shows the new choice', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'light' });
  await page.goto('/');
  const palette = await openCommandPaletteWithKeys(page);

  await palette.getByRole('option', { name: 'Use the dark theme' }).click();

  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await expect(page.locator('body')).toHaveCSS('background-color', 'rgb(22, 22, 22)');
  await expect(page.getByRole('banner').getByRole('button', { name: 'Theme: Dark' })).toBeVisible();
});
