// Bar chart on the instrument page, against the real backend with the IBKR fake. The fake has one bar for each bar
// period, and the e2e server clock is 2026-01-02 03:04:05 UTC (backend/tests/e2e_server.py).
import { expect, test, type Locator } from '@playwright/test';

/** The color of the chart background: a pixel near the top left corner of the largest chart canvas. */
async function readChartBackground(chart: Locator): Promise<string> {
  return chart.evaluate((element) => {
    const canvases = Array.from(element.querySelectorAll('canvas'));
    const largest = canvases.reduce((first, second) => (second.width * second.height > first.width * first.height ? second : first));
    const pixel = largest.getContext('2d')?.getImageData(2, 2, 1, 1).data;
    return pixel === undefined ? '' : `rgb(${String(pixel[0])}, ${String(pixel[1])}, ${String(pixel[2])})`;
  });
}

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

test('changes the bar period with a click and keeps it in the page address', async ({ page }) => {
  await page.goto('/instruments/SEHK/700?currency=HKD&bar_period=1-HOUR');
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('2160 bars');
  const barPeriods = page.getByRole('tablist', { name: 'Bar period' });
  await expect(barPeriods.getByRole('tab', { name: '1 hour' })).toHaveAttribute('aria-selected', 'true');

  await barPeriods.getByRole('tab', { name: '1 day' }).click();

  await expect(page).toHaveURL('/instruments/SEHK/700?currency=HKD&bar_period=1-DAY');
  await expect(barPeriods.getByRole('tab', { name: '1 day' })).toHaveAttribute('aria-selected', 'true');
  // The default range of daily bars is 1096 days: from 2023-01-02 to 2026-01-01, both included.
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('1096 bars');
  await expect(page.getByRole('img', { name: 'Bar chart of 700 / SEHK / HKD, 1-DAY bars' })).toBeVisible();
});

test('changes the bar period with the arrow keys, Home, and End', async ({ page }) => {
  await page.goto('/instruments/SEHK/700?currency=HKD&bar_period=1-HOUR');
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('2160 bars');
  const barPeriods = page.getByRole('tablist', { name: 'Bar period' });
  await barPeriods.getByRole('tab', { name: '1 hour' }).focus();

  // Each key selects a tab, and the chart opens the bars of that bar period. The selected tab keeps the focus.
  const steps = [
    { key: 'ArrowRight', tab: '1 day', barPeriod: '1-DAY' },
    { key: 'Home', tab: '1 minute', barPeriod: '1-MINUTE' },
    { key: 'ArrowRight', tab: '5 minutes', barPeriod: '5-MINUTE' },
    { key: 'End', tab: '1 day', barPeriod: '1-DAY' },
    { key: 'ArrowLeft', tab: '1 hour', barPeriod: '1-HOUR' },
  ];
  for (const step of steps) {
    await page.keyboard.press(step.key);
    const tab = barPeriods.getByRole('tab', { name: step.tab, exact: true });
    await expect(tab).toBeFocused();
    await expect(tab).toHaveAttribute('aria-selected', 'true');
    await expect(page).toHaveURL(`/instruments/SEHK/700?currency=HKD&bar_period=${step.barPeriod}`);
    await expect(page.getByRole('img', { name: `Bar chart of 700 / SEHK / HKD, ${step.barPeriod} bars` })).toBeVisible();
  }
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('2160 bars');
});

test('a watchlist link without a bar period opens daily bars', async ({ page }) => {
  await page.goto('/instruments/SEHK/9988?currency=HKD');

  const dailyTab = page.getByRole('tablist', { name: 'Bar period' }).getByRole('tab', { name: '1 day' });
  await expect(dailyTab).toHaveAttribute('aria-selected', 'true');
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

test('the chart takes the new color scheme without a page reload', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'light' });
  await page.goto('/instruments/SEHK/700?currency=HKD&bar_period=1-HOUR');
  const chart = page.getByRole('img', { name: 'Bar chart of 700 / SEHK / HKD, 1-HOUR bars' });
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('2160 bars');
  // The chart background is the Carbon token --cds-layer-01: #ffffff in g10, #262626 in g100.
  await expect.poll(() => readChartBackground(chart)).toBe('rgb(255, 255, 255)');

  await page.emulateMedia({ colorScheme: 'dark' });

  await expect.poll(() => readChartBackground(chart)).toBe('rgb(38, 38, 38)');
});
