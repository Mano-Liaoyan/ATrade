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

// Own panes (section 23.9.3 and 23.9.4). Each own indicator gets a new pane; the fourth goes into the last pane.

async function addIndicator(page: Page, optionName: RegExp): Promise<void> {
  await page.getByRole('button', { name: 'Add indicator' }).click();
  const dialog = page.getByRole('dialog', { name: 'Add indicator' });
  await dialog.getByRole('option', { name: optionName }).click();
  await expect(dialog).toBeHidden();
}

function paneOptions(page: Page, name: string): Locator {
  return page.getByRole('button', { name: `Options for ${name}` });
}

async function choosePaneOption(page: Page, name: string, item: string): Promise<void> {
  await paneOptions(page, name).click();
  await page.getByRole('menuitem', { name: item }).click();
  await expect(page.getByRole('menu')).toBeHidden();
}

async function readTop(locator: Locator): Promise<number> {
  const box = await locator.boundingBox();
  if (box === null) {
    throw new Error('The element has no box.');
  }
  return box.y;
}

async function addOwnIndicators(page: Page): Promise<void> {
  await addIndicator(page, /^RSI$/);
  await addIndicator(page, /^MACD$/);
  await addIndicator(page, /^ATR$/);
  await addIndicator(page, /^Realized volatility/);
}

test('own indicators get at most 3 own panes, and the fourth goes into the last pane', async ({ page }) => {
  await openChart(page);
  await addOwnIndicators(page);

  await expect(paneOptions(page, 'RSI 14')).toBeVisible();
  await expect(paneOptions(page, 'MACD 12 26 9')).toBeVisible();
  await expect(paneOptions(page, 'ATR 14')).toBeVisible();
  await expect(page.getByRole('button', { name: /^Options for / })).toHaveCount(4);
  // RV is in the legend of the last pane, after ATR.
  const lastLegend = page.getByRole('region', { name: 'Legend of ATR 14' }).getByRole('listitem');
  await expect(lastLegend).toHaveText([/^ATR 14/, /^RV 60/]);
  await expect(lastLegend.nth(1).locator('.legend-value')).toHaveText([/^-?\d+\.\d{2} %$/]);

  expect(await readTop(paneOptions(page, 'bars'))).toBeLessThan(await readTop(paneOptions(page, 'RSI 14')));
  expect(await readTop(paneOptions(page, 'RSI 14'))).toBeLessThan(await readTop(paneOptions(page, 'MACD 12 26 9')));
  expect(await readTop(paneOptions(page, 'MACD 12 26 9'))).toBeLessThan(await readTop(paneOptions(page, 'ATR 14')));
});

test('Move up changes the order of the own panes, and the first own pane has no Move up', async ({ page }) => {
  await openChart(page);
  await addOwnIndicators(page);

  await paneOptions(page, 'RSI 14').click();
  await expect(page.getByRole('menuitem')).toHaveText(['Move down', 'Maximize', 'Remove indicators']);
  await page.keyboard.press('Escape');
  await paneOptions(page, 'bars').click();
  await expect(page.getByRole('menuitem')).toHaveText(['Maximize']);
  await page.keyboard.press('Escape');

  await choosePaneOption(page, 'MACD 12 26 9', 'Move up');

  await expect
    .poll(async () => (await readTop(paneOptions(page, 'MACD 12 26 9'))) < (await readTop(paneOptions(page, 'RSI 14'))))
    .toBe(true);
  expect(await readTop(paneOptions(page, 'bars'))).toBeLessThan(await readTop(paneOptions(page, 'MACD 12 26 9')));
});

test('Maximize gives a pane all the chart height, and Restore gives back the heights', async ({ page }) => {
  await openChart(page);
  await addOwnIndicators(page);
  const macdLegend = page.getByRole('region', { name: 'Legend of MACD 12 26 9' });
  const topBefore = await readTop(macdLegend);

  await choosePaneOption(page, 'MACD 12 26 9', 'Maximize');

  // The other panes have no height: their legends and buttons go away.
  await expect(page.getByRole('button', { name: /^Options for / })).toHaveCount(1);
  await expect(paneOptions(page, 'bars')).toBeHidden();
  const chartTop = await readTop(page.getByRole('img', { name: CHART_NAME }));
  await expect.poll(async () => (await readTop(macdLegend)) - chartTop).toBeLessThan(20);

  await choosePaneOption(page, 'MACD 12 26 9', 'Restore');

  await expect(page.getByRole('button', { name: /^Options for / })).toHaveCount(4);
  await expect.poll(async () => Math.abs((await readTop(macdLegend)) - topBefore)).toBeLessThan(2);
});

test('Remove indicators removes the pane and all its indicators', async ({ page }) => {
  await openChart(page);
  await addOwnIndicators(page);

  await choosePaneOption(page, 'ATR 14', 'Remove indicators');

  await expect(page.getByRole('button', { name: /^Options for / })).toHaveCount(3);
  await expect(legendRow(page, 'ATR 14')).toHaveCount(0);
  await expect(legendRow(page, 'RV 60')).toHaveCount(0);
  await expect(legendRow(page, 'MACD 12 26 9')).toBeVisible();
});

test('a legend that is higher than its pane scrolls to its last row', async ({ page }) => {
  await openChart(page);
  await addOwnIndicators(page);
  // 6 more rows go into the last pane.
  for (const option of [/^12-1 momentum/, /^Distance to 52-week high/, /^Average trading value/, /^RSI$/, /^RSI$/, /^RSI$/]) {
    await addIndicator(page, option);
  }
  const region = page.getByRole('region', { name: 'Legend of ATR 14' });
  const lastRow = region.getByRole('listitem').last();
  await expect(region.getByRole('listitem')).toHaveCount(8);
  const track = page.getByRole('scrollbar', { name: 'Legend of ATR 14 scroll bar' });
  await expect(track).toBeVisible();
  await expect(lastRow).not.toBeInViewport({ ratio: 1 });

  await track.focus();
  await page.keyboard.press('End');

  await expect(lastRow).toBeInViewport({ ratio: 1 });
  const regionBox = await region.boundingBox();
  const rowBox = await lastRow.boundingBox();
  if (regionBox === null || rowBox === null) {
    throw new Error('The legend has no box.');
  }
  expect(rowBox.y + rowBox.height).toBeLessThanOrEqual(regionBox.y + regionBox.height + 1);
});
