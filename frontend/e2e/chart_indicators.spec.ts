// Indicators on the bar chart of the instrument page (docs/architecture/indicator.md section 23.9), against the real
// backend with the IBKR fake. The fake daily bars start on 2023-01-02 (the default range of 1096 days), so a 20-bar
// indicator has no value at the first 19 bars: the series route has no saved warm-up bars before them.
import { expect, test, type Locator, type Page } from '@playwright/test';

const PAGE_PATH = '/instruments/SEHK/700?currency=HKD&bar_period=1-DAY';
const CHART_NAME = 'Bar chart of 700 / SEHK / HKD, 1-DAY bars';
const NUMBER_PATTERN = /^\d{1,3}(,\d{3})*\.\d{2}$/;

async function openChart(page: Page): Promise<void> {
  await page.goto(PAGE_PATH);
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('1096 bars');
}

function legendRow(page: Page, name: string): Locator {
  return page.getByRole('list', { name: 'Legend' }).getByRole('listitem').filter({ hasText: name });
}

async function readRowValues(row: Locator): Promise<string[]> {
  return row.locator('.legend-value').allTextContents();
}

/** Moves the pointer over the chart at `fraction` of the width of the plot area (left of the price scale). */
async function moveCrosshair(page: Page, fraction: number): Promise<void> {
  const chart = page.getByRole('img', { name: CHART_NAME });
  const box = await chart.boundingBox();
  if (box === null) {
    throw new Error('The chart has no box.');
  }
  // The price scale on the right is less than 80 pixels wide.
  const plotWidth = box.width - 80;
  await page.mouse.move(box.x + Math.max(1, plotWidth * fraction), box.y + box.height / 2);
}

test('/ opens Add indicator, the search finds Bollinger Bands, and Enter adds it to the legend', async ({ page }) => {
  await openChart(page);
  await expect(page.getByRole('button', { name: 'Add indicator' })).toBeVisible();

  await page.locator('body').press('/');

  const dialog = page.getByRole('dialog', { name: 'Add indicator' });
  await expect(dialog).toBeVisible();
  const options = dialog.getByRole('option');
  await expect(options).toHaveCount(11);
  await expect(options.first()).toHaveText('SMA');
  await expect(options.nth(9)).toHaveText(/^Bollinger Bands\s*BB$/);
  await page.keyboard.type('boll');
  await expect(options).toHaveCount(1);
  await page.keyboard.press('Enter');

  await expect(dialog).toBeHidden();
  const row = legendRow(page, 'BB 20 2');
  await expect(row).toBeVisible();
  // The crosshair is not on the chart: the values of the last bar. Upper, middle, and lower.
  await expect(row.locator('.legend-value')).toHaveText([NUMBER_PATTERN, NUMBER_PATTERN, NUMBER_PATTERN]);
});

test('the legend values follow the crosshair and show "No value" at a bar without a value', async ({ page }) => {
  await openChart(page);
  await page.getByRole('button', { name: 'Add indicator' }).click();
  const dialog = page.getByRole('dialog', { name: 'Add indicator' });
  await dialog.getByRole('option', { name: /Bollinger Bands/ }).click();
  await expect(dialog).toBeHidden();
  const row = legendRow(page, 'BB 20 2');
  await expect(row.locator('.legend-value')).toHaveText([NUMBER_PATTERN, NUMBER_PATTERN, NUMBER_PATTERN]);
  const lastBarValues = await readRowValues(row);

  await moveCrosshair(page, 0.5);
  await expect.poll(() => readRowValues(row)).not.toEqual(lastBarValues);
  await expect(row.locator('.legend-value')).toHaveText([NUMBER_PATTERN, NUMBER_PATTERN, NUMBER_PATTERN]);
  const middleValues = await readRowValues(row);

  await moveCrosshair(page, 0.53);
  await expect.poll(() => readRowValues(row)).not.toEqual(middleValues);

  // The first bars of the chart have no value.
  await moveCrosshair(page, 0);
  await expect.poll(() => readRowValues(row)).toEqual(['No value', 'No value', 'No value']);
});

test('the Add indicator dialog closes with Escape without a new indicator', async ({ page }) => {
  await openChart(page);
  await page.getByRole('button', { name: 'Add indicator' }).click();
  const dialog = page.getByRole('dialog', { name: 'Add indicator' });
  await expect(dialog).toBeVisible();

  await page.keyboard.press('Escape');

  await expect(dialog).toBeHidden();
  await expect(page.getByRole('list', { name: 'Legend' }).getByRole('listitem')).toHaveCount(1);
});
