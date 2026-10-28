// The instrument page is a workbench (#102): it fills the window below the header and does not scroll as a page.
// The watchlist column collapses, the chart panel and the paper account panel minimize and maximize, and the
// browser keeps the layout. Against the real backend with the IBKR fake (backend/tests/e2e_server.py).
import { expect, test, type Locator, type Page } from '@playwright/test';

const PAGE_PATH = '/instruments/SEHK/700?currency=HKD&bar_period=1-HOUR';
const CHART_NAME = 'Bar chart of 700 / SEHK / HKD, 1-HOUR bars';

async function openWorkbench(page: Page): Promise<void> {
  await page.goto(PAGE_PATH);
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('2160 bars');
}

async function readBox(locator: Locator): Promise<{ width: number; height: number; bottom: number }> {
  const box = await locator.boundingBox();
  if (box === null) {
    throw new Error('The element has no box.');
  }
  return { width: box.width, height: box.height, bottom: box.y + box.height };
}

function chartPanel(page: Page): Locator {
  return page.getByRole('region', { name: '700 / SEHK / HKD' });
}

function accountPanel(page: Page): Locator {
  return page.getByRole('region', { name: 'Paper account' });
}

test('the page fills the window and the chart rescales with the window', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await openWorkbench(page);
  const chart = page.getByRole('img', { name: CHART_NAME });

  const hasPageScroll = await page.evaluate(() => {
    const root = document.documentElement;
    return root.scrollHeight > root.clientHeight || root.scrollWidth > root.clientWidth;
  });
  expect(hasPageScroll).toBe(false);
  const firstBox = await readBox(chart);

  await page.setViewportSize({ width: 1280, height: 640 });

  await expect.poll(async () => (await readBox(chart)).height).toBeLessThan(firstBox.height - 100);
  await expect.poll(() => chart.locator('canvas').first().evaluate((canvas) => canvas.getBoundingClientRect().height)).toBeLessThan(
    firstBox.height - 100,
  );
});

test('the chart rescales when the watchlist collapses and opens, and the browser keeps the choice', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await openWorkbench(page);
  const chart = page.getByRole('img', { name: CHART_NAME });
  const firstWidth = (await readBox(chart)).width;

  await page.getByRole('button', { name: 'Collapse watchlist' }).click();

  await expect(page.getByRole('region', { name: 'Watchlist table' })).toBeHidden();
  await expect.poll(async () => (await readBox(chart)).width).toBeGreaterThan(firstWidth + 100);
  await expect.poll(() => chart.locator('canvas').first().evaluate((canvas) => canvas.getBoundingClientRect().width)).toBeGreaterThan(
    firstWidth + 100,
  );

  await page.reload();
  await expect(page.getByRole('button', { name: 'Open watchlist' })).toBeVisible();

  await page.getByRole('button', { name: 'Open watchlist' }).click();

  await expect(page.getByRole('region', { name: 'Watchlist table' })).toBeVisible();
  await expect.poll(async () => Math.round((await readBox(chart)).width)).toBe(Math.round(firstWidth));
});

test('a panel minimizes and restores with its buttons', async ({ page }) => {
  await openWorkbench(page);
  const chart = page.getByRole('img', { name: CHART_NAME });

  await chartPanel(page).getByRole('button', { name: 'Minimize panel' }).click();

  await expect(chart).toBeHidden();
  await expect(page.getByRole('separator', { name: 'Resize the chart and the paper account' })).toBeHidden();
  await expect(accountPanel(page).getByRole('tablist', { name: 'Paper account' })).toBeVisible();

  await chartPanel(page).getByRole('button', { name: 'Restore panel' }).click();

  await expect(chart).toBeVisible();
  await expect(page.getByRole('separator', { name: 'Resize the chart and the paper account' })).toBeVisible();
});

test('a maximized panel restores with Escape, and the browser keeps the panel layout', async ({ page }) => {
  await openWorkbench(page);
  const chart = page.getByRole('img', { name: CHART_NAME });

  await accountPanel(page).getByRole('button', { name: 'Maximize panel' }).click();

  await expect(chart).toBeHidden();
  await expect(chartPanel(page).getByRole('heading', { name: '700 / SEHK / HKD' })).toBeVisible();

  await page.reload();
  await expect(chart).toBeHidden();
  await expect(accountPanel(page).getByRole('button', { name: 'Restore panel' })).toBeVisible();

  await page.keyboard.press('Escape');

  await expect(chart).toBeVisible();
  await expect(accountPanel(page).getByRole('button', { name: 'Maximize panel' })).toBeVisible();
});

test('Escape restores the maximized panel while the focus is in the panels', async ({ page }) => {
  await openWorkbench(page);

  // The Maximize button keeps the focus.
  await chartPanel(page).getByRole('button', { name: 'Maximize panel' }).click();
  await expect(chartPanel(page).getByRole('button', { name: 'Restore panel' })).toBeFocused();
  await page.keyboard.press('Escape');

  await expect(page.getByRole('separator', { name: 'Resize the chart and the paper account' })).toBeVisible();
  await expect(chartPanel(page).getByRole('button', { name: 'Maximize panel' })).toBeVisible();
});

test('a double-click on the empty part of a header line maximizes the panel', async ({ page }) => {
  await openWorkbench(page);
  const header = page.getByRole('tablist', { name: 'Paper account' }).locator('xpath=ancestor::*[contains(@class, "panel-header")][1]');
  const headerBox = await header.boundingBox();
  if (headerBox === null) {
    throw new Error('The header line has no box.');
  }
  const tabsBox = await readBox(page.getByRole('tablist', { name: 'Paper account' }));

  // The empty part is between the tabs and the panel buttons.
  await page.mouse.dblclick(headerBox.x + tabsBox.width + 40, headerBox.y + headerBox.height / 2);

  await expect(page.getByRole('img', { name: CHART_NAME })).toBeHidden();
  await expect(accountPanel(page).getByRole('button', { name: 'Restore panel' })).toBeVisible();
});

test('the splitter changes the panel heights with the arrow keys', async ({ page }) => {
  await openWorkbench(page);
  const splitter = page.getByRole('separator', { name: 'Resize the chart and the paper account' });
  const firstValue = Number(await splitter.getAttribute('aria-valuenow'));
  const firstHeight = (await readBox(accountPanel(page))).height;

  await splitter.focus();
  await page.keyboard.press('ArrowUp');
  await page.keyboard.press('ArrowUp');

  await expect(splitter).toHaveAttribute('aria-valuenow', String(firstValue + 32));
  await expect.poll(async () => Math.round((await readBox(accountPanel(page))).height)).toBe(Math.round(firstHeight + 32));

  // Home gives the paper account panel its minimum height, End its maximum height.
  await page.keyboard.press('Home');
  await expect(splitter).toHaveAttribute('aria-valuenow', '96');
  await page.keyboard.press('End');
  await expect(splitter).toHaveAttribute('aria-valuenow', (await splitter.getAttribute('aria-valuemax')) ?? '');
  await expect(splitter).toHaveAttribute('aria-controls', /.+/);
});

test('a watchlist instrument opens its page with the same bar period', async ({ page, request }) => {
  // The browser projects share one database: another project can add AAPL first (409).
  // eslint-disable-next-line @typescript-eslint/naming-convention -- `data` is the request body option of Playwright.
  const response = await request.post('/api/watchlist', { data: { symbol: 'AAPL', exchange: 'NASDAQ', currency: 'USD' } });
  expect([201, 409]).toContain(response.status());
  await openWorkbench(page);

  await page.getByRole('complementary', { name: 'Watchlist' }).getByRole('link', { name: 'AAPL', exact: true }).click();

  await expect(page).toHaveURL('/instruments/NASDAQ/AAPL?currency=USD&bar_period=1-HOUR');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('AAPL / NASDAQ / USD');
  await expect(page.getByRole('tablist', { name: 'Bar period' }).getByRole('tab', { name: '1 hour', exact: true })).toHaveAttribute(
    'aria-selected',
    'true',
  );
});

test('the paper account panel shows the positions, the open orders, and the filled orders of today', async ({ page }) => {
  await openWorkbench(page);
  const tabs = accountPanel(page).getByRole('tablist', { name: 'Paper account' });

  await expect(tabs.getByRole('tab', { name: /^Positions/ })).toHaveAttribute('aria-selected', 'true');
  await tabs.getByRole('tab', { name: /^Open orders/ }).click();
  await expect(tabs.getByRole('tab', { name: /^Open orders/ })).toHaveAttribute('aria-selected', 'true');
  await tabs.getByRole('tab', { name: /^Filled today/ }).click();
  await expect(tabs.getByRole('tab', { name: /^Filled today/ })).toHaveAttribute('aria-selected', 'true');
});

test('the order column keeps the paper order form and collapses to a rail', async ({ page }) => {
  await openWorkbench(page);

  await expect(page.getByRole('form', { name: 'Paper order' })).toBeVisible();
  await page.getByRole('button', { name: 'Collapse paper order' }).click();
  await expect(page.getByRole('form', { name: 'Paper order' })).toBeHidden();
  await page.getByRole('button', { name: 'Open paper order' }).click();
  await expect(page.getByRole('form', { name: 'Paper order' })).toBeVisible();
});
