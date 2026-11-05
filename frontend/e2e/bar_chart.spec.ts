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
  await expect(page.getByRole('link', { name: 'TradingView', exact: true })).toHaveCount(0);
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

// The older bar tests use their own instrument: the older bars that they save would give the 700 indicators of
// chart_indicators.spec.ts warm-up bars.

/** Drags the chart to the right, so that the view moves to older bars. */
async function dragChartToTheRight(chart: Locator): Promise<void> {
  const box = await chart.locator('canvas').first().boundingBox();
  if (box === null) {
    throw new Error('The chart has no canvas box.');
  }
  const y = box.y + box.height / 2;
  await chart.page().mouse.move(box.x + box.width / 3, y);
  await chart.page().mouse.down();
  await chart.page().mouse.move(box.x + (box.width * 2) / 3, y, { steps: 10 });
  await chart.page().mouse.up();
}

test('a drag to the left end of the chart loads the next older bars', async ({ page }) => {
  const olderBarRequests: string[] = [];
  page.on('request', (request) => {
    if (request.url().includes('/api/market-data/bars?') && request.url().includes('start_utc=')) {
      olderBarRequests.push(request.url());
    }
  });
  await page.goto('/instruments/SEHK/388?currency=HKD&bar_period=1-DAY');
  const chart = page.getByRole('img', { name: 'Bar chart of 388 / SEHK / HKD, 1-DAY bars' });
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('1096 bars');
  // The first fit shows the first bar: only a move of the user loads older bars.
  expect(olderBarRequests).toEqual([]);

  await dragChartToTheRight(chart);

  // The first bar is 2023-01-02: the next range is the 1096 days before it.
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('2192 bars');
  expect(olderBarRequests).toHaveLength(1);
  const olderRange = new URL(olderBarRequests[0] ?? '').searchParams;
  expect(olderRange.get('start_utc')).toBe('2020-01-02T00:00:00.000Z');
  expect(olderRange.get('end_utc')).toBe('2023-01-02T00:00:00.000Z');
});

test('the chart stops loading older bars after an empty answer', async ({ page }) => {
  let olderBarRequestCount = 0;
  await page.route('**/api/market-data/bars?*start_utc=*', async (route) => {
    olderBarRequestCount += 1;
    await route.fulfill({ json: { bars: [] } });
  });
  await page.goto('/instruments/SEHK/388?currency=HKD&bar_period=1-DAY');
  const chart = page.getByRole('img', { name: 'Bar chart of 388 / SEHK / HKD, 1-DAY bars' });
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('1096 bars');

  await dragChartToTheRight(chart);
  await expect.poll(() => olderBarRequestCount).toBe(1);
  await dragChartToTheRight(chart);

  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('1096 bars');
  expect(olderBarRequestCount).toBe(1);
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

test('the chart takes the theme of the theme button without a new chart', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'light' });
  await page.goto('/instruments/SEHK/700?currency=HKD&bar_period=1-HOUR');
  const chart = page.getByRole('img', { name: 'Bar chart of 700 / SEHK / HKD, 1-HOUR bars' });
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('2160 bars');
  await expect.poll(() => readChartBackground(chart)).toBe('rgb(255, 255, 255)');
  // A mark on each canvas of the chart. A new chart has new canvases without the mark.
  await chart.evaluate((element) => {
    for (const canvas of element.querySelectorAll('canvas')) {
      canvas.dataset.firstChart = 'true';
    }
  });
  const header = page.getByRole('banner');

  await header.getByRole('button', { name: 'Theme: System' }).click();
  await header.getByRole('button', { name: 'Theme: Light' }).click();

  await expect(header.getByRole('button', { name: 'Theme: Dark' })).toBeVisible();
  await expect.poll(() => readChartBackground(chart)).toBe('rgb(38, 38, 38)');
  await expect(chart.locator('canvas:not([data-first-chart])')).toHaveCount(0);
});
