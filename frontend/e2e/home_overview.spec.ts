// The home page is the account overview workbench (#108): the watchlist column, the key numbers of the paper account,
// the Positions panel, and the Orders panel. With the IBKR fake of backend/tests/e2e_server.py: account DU1234567,
// a balance, 40 positions, and 30 open orders of forward test 42. The owner ledger of "By hand" has 10 shares of each
// position, but only 5 of TEST05.
import { expect, test, type Locator, type Page } from '@playwright/test';

function positionsPanel(page: Page): Locator {
  return page.getByRole('region', { name: 'Positions', exact: true }).first();
}

function ordersPanel(page: Page): Locator {
  return page.getByRole('region', { name: 'Orders', exact: true });
}

test('the home page fills the window and shows the key numbers of the paper account', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto('/');

  const balance = page.locator('dl[aria-label="Paper account balance"]');
  await expect(balance.getByRole('term')).toHaveText(['Net liquidation (USD)', 'Cash (USD)']);
  await expect(balance.getByRole('definition')).toHaveText(['101,234.50', '25,000.00']);
  await expect(page.getByRole('complementary', { name: 'Watchlist' })).toBeVisible();
  await expect(positionsPanel(page).getByRole('heading', { name: 'Positions (40)' })).toBeVisible();
  await expect(ordersPanel(page).getByRole('tab', { name: /^Open orders/ })).toHaveAttribute('aria-selected', 'true');
  const hasPageScroll = await page.evaluate(() => {
    const root = document.documentElement;
    return root.scrollHeight > root.clientHeight || root.scrollWidth > root.clientWidth;
  });
  expect(hasPageScroll).toBe(false);
});

test('the Positions table shows the owner of each row and the unattributed difference', async ({ page }) => {
  await page.goto('/');
  const table = positionsPanel(page);

  await expect(table.getByRole('columnheader', { name: 'Owner' })).toBeVisible();
  await expect(table.getByRole('row', { name: /TEST01/ })).toContainText('By hand');
  const rows = table.getByRole('row', { name: /TEST05/ });
  await expect(rows).toHaveCount(2);
  await expect(rows.nth(0)).toContainText('By hand');
  await expect(rows.nth(0).getByRole('cell').nth(2)).toHaveText('5');
  const unattributed = rows.nth(1);
  await expect(unattributed).toContainText('Unattributed: 5');
  await expect(unattributed.locator('.status-indicator--warning svg')).toBeAttached();
});

test('the home page has no paper order form', async ({ page }) => {
  await page.goto('/');
  await expect(ordersPanel(page).getByRole('row', { name: /FTO01/ })).toBeAttached();

  await expect(page.getByRole('main').getByRole('form')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Review order' })).toHaveCount(0);
});

test('the watchlist rows and the position rows are 32px high', async ({ page, request }) => {
  // The browser projects share one database: another project can add AAPL first (409).
  // eslint-disable-next-line @typescript-eslint/naming-convention -- `data` is the request body option of Playwright.
  const response = await request.post('/api/watchlist', { data: { symbol: 'AAPL', exchange: 'NASDAQ', currency: 'USD' } });
  expect([201, 409]).toContain(response.status());
  await page.goto('/');
  const watchlistRow = page.getByRole('region', { name: 'Watchlist table' }).getByRole('row', { name: /^AAPL/ });
  // The change column has an arrow icon after the daily bars load. The row also has the Delete button.
  await expect(watchlistRow.getByText(/%$/).locator('svg')).toBeVisible();
  await expect(watchlistRow.getByRole('button', { name: /^Delete AAPL/ })).toBeVisible();

  await expect.poll(async () => Math.round((await watchlistRow.boundingBox())?.height ?? 0)).toBe(32);
  const positionRow = positionsPanel(page).getByRole('row', { name: /TEST01/ });
  await expect.poll(async () => Math.round((await positionRow.boundingBox())?.height ?? 0)).toBe(32);
});

test('position table has a visible scroll track and its last row can be scrolled into view', async ({ page }) => {
  await page.goto('/');
  const lastRow = positionsPanel(page).getByRole('row', { name: /TEST40/ });
  const track = page.getByRole('scrollbar', { name: 'Positions scroll bar' });
  const thumb = track.locator('.scroll-thumb');

  await expect(positionsPanel(page).getByRole('row', { name: /TEST01/ })).toBeInViewport();
  await expect(track).toBeVisible();
  await expect(thumb).toBeVisible();
  await expect(lastRow).not.toBeInViewport();

  await track.focus();
  await page.keyboard.press('End');

  await expect(lastRow).toBeInViewport();
  await expect(thumb).toBeVisible();
  await expect(track).toHaveAttribute('aria-valuenow', '100');
});

test('the Positions panel maximizes and restores with Escape', async ({ page }) => {
  await page.goto('/');
  const splitter = page.getByRole('separator', { name: 'Resize the positions and the orders' });
  await expect(splitter).toBeVisible();

  await positionsPanel(page).getByRole('button', { name: 'Maximize panel' }).click();

  await expect(splitter).toBeHidden();
  await expect(page.getByRole('region', { name: 'Open orders' })).toBeHidden();
  await page.keyboard.press('Escape');
  await expect(splitter).toBeVisible();
  await expect(page.getByRole('region', { name: 'Open orders' })).toBeVisible();
});

test('the Orders panel shows the filled orders of today', async ({ page }) => {
  await page.goto('/');
  const tabs = ordersPanel(page).getByRole('tablist', { name: 'Orders' });

  await tabs.getByRole('tab', { name: /^Filled today/ }).click();

  await expect(tabs.getByRole('tab', { name: /^Filled today/ })).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByRole('region', { name: 'Open orders' })).toHaveCount(0);
});
