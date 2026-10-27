// Bar chart on the instrument page, against the real backend with the IBKR fake. The fake has one bar for each bar
// period, and the e2e server clock is 2026-01-02 03:04:05 UTC (backend/tests/e2e_server.py).
import { expect, test } from '@playwright/test';

test('opens the bar chart of an instrument with the TradingView attribution', async ({ page }) => {
  await page.goto('/instruments/SEHK/700?currency=HKD&bar_period=1-HOUR');

  await expect(page.getByRole('heading', { level: 1 })).toHaveText('700 / SEHK / HKD');
  // The default range of 1 hour bars is 90 days: 90 * 24 complete bars.
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('2160 bars');
  const chart = page.getByRole('img', { name: 'Bar chart of 700 / SEHK / HKD, 1-HOUR bars' });
  await expect(chart.locator('canvas').first()).toBeVisible();
  await expect(chart.getByRole('link', { name: 'Charting by TradingView' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'TradingView', exact: true })).toHaveAttribute(
    'href',
    'https://www.tradingview.com/',
  );
});

test('changes the bar period and keeps it in the page address', async ({ page }) => {
  await page.goto('/instruments/SEHK/700?currency=HKD&bar_period=1-HOUR');
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('2160 bars');

  await page.getByLabel('Bar period').selectOption('1-DAY');

  await expect(page).toHaveURL('/instruments/SEHK/700?currency=HKD&bar_period=1-DAY');
  // The default range of daily bars is 1096 days: from 2023-01-02 to 2026-01-01, both included.
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('1096 bars');
  await expect(page.getByRole('img', { name: 'Bar chart of 700 / SEHK / HKD, 1-DAY bars' })).toBeVisible();
});

test('a watchlist link without a bar period opens daily bars', async ({ page }) => {
  await page.goto('/instruments/SEHK/9988?currency=HKD');

  await expect(page.getByLabel('Bar period')).toHaveValue('1-DAY');
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('1096 bars');
});

test('the chart receives live bar updates over the WebSocket', async ({ page }) => {
  await page.goto('/instruments/SEHK/700?currency=HKD&bar_period=1-HOUR');
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('2160 bars');

  // The fake updates the current bar (2026-01-02 03:00 UTC, open 123) a few times each second: the close moves up
  // 0.25 for each update, from 123 to 124.75, and starts again.
  const liveBar = page.getByRole('status', { name: 'Live bar' });
  await expect(liveBar).toHaveText(/^Live bar 2026-01-02 03:00 UTC: close 12[34]\.\d+$/);
  const firstText = (await liveBar.textContent()) ?? '';
  await expect(liveBar).not.toHaveText(firstText);
  await expect(liveBar).toHaveText(/^Live bar 2026-01-02 03:00 UTC: close 12[34]\.\d+$/);
});
