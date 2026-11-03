// Indicators on the bar chart of the instrument page (docs/architecture/indicator.md section 23.9), against the real
// backend with the IBKR fake. The fake daily bars start on 2023-01-02 (the default range of 1096 days), so a 20-bar
// indicator has no value at the first 19 bars: the series route has no saved warm-up bars before them.
import { expect, test, type Locator, type Page } from '@playwright/test';
import { useLocalChartIndicatorSet, type LocalChartIndicatorSet } from './local_chart_indicator_set';

const PAGE_PATH = '/instruments/SEHK/700?currency=HKD&bar_period=1-DAY';
const CHART_NAME = 'Bar chart of 700 / SEHK / HKD, 1-DAY bars';
const NUMBER_PATTERN = /^\d{1,3}(,\d{3})*\.\d{2}$/;

// Each test starts with an empty chart indicator set of its own.
let chartIndicatorSet: LocalChartIndicatorSet;
test.beforeEach(async ({ context }) => {
  chartIndicatorSet = await useLocalChartIndicatorSet(context);
});

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
  // WebKit gives a fully shown row a ratio a bit under 1 (sub-pixel heights).
  await expect(lastRow).not.toBeInViewport({ ratio: 0.9 });

  await track.focus();
  await page.keyboard.press('End');

  await expect(lastRow).toBeInViewport({ ratio: 0.99 });
  const regionBox = await region.boundingBox();
  const rowBox = await lastRow.boundingBox();
  if (regionBox === null || rowBox === null) {
    throw new Error('The legend has no box.');
  }
  expect(rowBox.y + rowBox.height).toBeLessThanOrEqual(regionBox.y + regionBox.height + 1);
});

// Legend row buttons and the settings popover (section 23.9.4 and 23.9.5).

// The number of canvas pixels of the chart in the color `hex` (a line color). The live bars change the candlesticks,
// so the tests look for the line color, not for a full picture.
async function countColorPixels(page: Page, hex: string): Promise<number> {
  return page.getByRole('img', { name: CHART_NAME }).evaluate((chart, color) => {
    const target = [1, 3, 5].map((start) => Number.parseInt(color.slice(start, start + 2), 16));
    let count = 0;
    for (const canvas of chart.querySelectorAll('canvas')) {
      const context = canvas.getContext('2d');
      if (context === null || canvas.width === 0 || canvas.height === 0) {
        continue;
      }
      const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
      for (let index = 0; index < pixels.length; index += 4) {
        if (target.every((value, channel) => Math.abs((pixels[index + channel] ?? 0) - value) <= 6) && (pixels[index + 3] ?? 0) > 200) {
          count += 1;
        }
      }
    }
    return count;
  }, hex);
}

// The first palette colors: purple 70 (light) and purple 60 (dark).
const LIGHT_COLOR_1 = '#6929c4';
const DARK_COLOR_1 = '#8a3ffc';
// Antialiasing gives some pixels of other lines a near color; a drawn line gives many more.
const LINE_PIXELS = 200;

async function hoverRow(page: Page, name: string): Promise<Locator> {
  const row = legendRow(page, name);
  await row.hover();
  return row;
}

async function addSma(page: Page): Promise<Locator> {
  await addIndicator(page, /^SMA$/);
  const row = legendRow(page, 'SMA 50');
  await expect(row.locator('.legend-value')).toHaveText([NUMBER_PATTERN]);
  return row;
}

test('Tab to a legend row shows its buttons', async ({ page }) => {
  await openChart(page);
  await addSma(page);
  const hideButton = page.getByRole('button', { name: 'Hide SMA 50' });
  const action = (name: string): Locator => page.locator('.legend-action').filter({ has: page.getByRole('button', { name }) });
  await expect(action('Hide SMA 50')).toHaveCSS('opacity', '0');

  await page.getByRole('button', { name: 'Add indicator' }).focus();
  // The legend comes after the header buttons and before the pane options button in the tab order.
  for (let step = 0; step < 40 && !(await hideButton.evaluate((element) => element === document.activeElement)); step += 1) {
    await page.keyboard.press('Tab');
  }

  await expect(hideButton).toBeFocused();
  for (const name of ['Hide SMA 50', 'Settings for SMA 50', 'Remove SMA 50']) {
    await expect(action(name)).toHaveCSS('opacity', '1');
  }
});

test('Hide takes the line away and keeps the row, and Show gives it back', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'light' });
  await openChart(page);
  await addSma(page);
  await expect.poll(() => countColorPixels(page, LIGHT_COLOR_1)).toBeGreaterThan(LINE_PIXELS);
  const shownNameColor = await legendRow(page, 'SMA 50').locator('.legend-name').evaluate((element) => getComputedStyle(element).color);

  const row = await hoverRow(page, 'SMA 50');
  await row.getByRole('button', { name: 'Hide SMA 50' }).click();

  await expect(row.locator('.legend-value')).toHaveCount(0);
  // The name takes the disabled text color.
  await expect(row.locator('.legend-name')).not.toHaveCSS('color', shownNameColor);
  await expect.poll(() => countColorPixels(page, LIGHT_COLOR_1)).toBeLessThan(LINE_PIXELS);
  // The Show button stays visible without the pointer or the focus on the row.
  await page.mouse.move(0, 0);
  await page.evaluate(() => {
    (document.activeElement as HTMLElement | null)?.blur();
  });
  await expect(page.locator('.legend-action').filter({ has: page.getByRole('button', { name: 'Show SMA 50' }) })).toHaveCSS('opacity', '1');
  await expect(page.locator('.legend-action').filter({ has: page.getByRole('button', { name: 'Remove SMA 50' }) })).toHaveCSS('opacity', '0');

  await row.getByRole('button', { name: 'Show SMA 50' }).click();

  await expect(row.locator('.legend-value')).toHaveText([NUMBER_PATTERN]);
  await expect.poll(() => countColorPixels(page, LIGHT_COLOR_1)).toBeGreaterThan(LINE_PIXELS);
});

test('the settings change SMA to 20 and its color to the third color, and the legend shows the backend values', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'light' });
  await openChart(page);
  const row = await addSma(page);

  await hoverRow(page, 'SMA 50');
  await row.getByRole('button', { name: 'Settings for SMA 50' }).click();
  const settings = page.getByRole('dialog', { name: 'SMA' });
  await expect(settings.getByRole('heading', { name: 'SMA' })).toBeVisible();
  await settings.getByRole('spinbutton', { name: 'Period' }).fill('20');
  // The third color of the light palette.
  await settings.getByRole('group', { name: 'Line' }).getByRole('radio', { name: 'Teal 70' }).check();
  const seriesResponse = page.waitForResponse(
    (response) => response.url().endsWith('/api/market-data/indicator-series') && (response.request().postData() ?? '').includes('"period":20'),
  );
  await settings.getByRole('button', { name: 'Apply' }).click();

  await expect(settings).toBeHidden();
  const body = (await (await seriesResponse).json()) as { series: { indicator: string; outputs: { value: (number | null)[] } }[] };
  const values = body.series.find((series) => series.indicator === 'sma')?.outputs.value ?? [];
  const lastValue = values.at(-1);
  if (lastValue === null || lastValue === undefined) {
    throw new Error('The series route gave no last SMA value.');
  }
  const expected = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(lastValue);
  const changedRow = legendRow(page, 'SMA 20');
  await expect(changedRow.locator('.legend-value')).toHaveText([expected]);
  await expect(changedRow.locator('.legend-value')).toHaveCSS('color', 'rgb(0, 93, 93)');
});

test('Apply is disabled with the reason while a parameter is invalid, and Escape closes without a change', async ({ page }) => {
  await openChart(page);
  await addIndicator(page, /^MACD$/);
  const row = legendRow(page, 'MACD 12 26 9');
  await expect(row).toBeVisible();
  await row.locator('.legend-name').click();
  const settings = page.getByRole('dialog', { name: 'MACD' });
  const apply = settings.getByRole('button', { name: 'Apply' });
  // The MACD fields are higher than the popover: they scroll with a visible track.
  await expect(page.getByRole('scrollbar', { name: 'Settings of MACD scroll bar' })).toBeVisible();

  const fastPeriod = settings.getByRole('spinbutton', { name: 'Fast period' });
  await fastPeriod.fill('30');
  await expect(settings.getByText('Fast period must be less than slow period (26).')).toBeVisible();
  await expect(fastPeriod).toHaveAttribute('aria-invalid', 'true');
  await expect(apply).toBeDisabled();
  await expect(apply).toHaveAccessibleDescription('Fix Fast period to apply.');
  await expect(settings.getByText('Fix Fast period to apply.')).toBeVisible();
  await fastPeriod.fill('0');
  await expect(settings.getByText(/^Enter a value from 1 to \d+\.$/)).toBeVisible();
  await expect(apply).toBeDisabled();

  await settings.getByRole('button', { name: 'Reset to defaults' }).click();
  await expect(fastPeriod).toHaveValue('12');
  await expect(apply).toBeEnabled();
  await expect(settings.getByText('Fix Fast period to apply.')).toHaveCount(0);
  await fastPeriod.fill('5');
  await page.keyboard.press('Escape');

  await expect(settings).toBeHidden();
  await expect(legendRow(page, 'MACD 12 26 9')).toBeVisible();
  await expect(legendRow(page, 'MACD 5 26 9')).toHaveCount(0);
});

test('Remove takes the row and the line away', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'light' });
  await openChart(page);
  const row = await addSma(page);
  await expect.poll(() => countColorPixels(page, LIGHT_COLOR_1)).toBeGreaterThan(LINE_PIXELS);

  await hoverRow(page, 'SMA 50');
  await row.getByRole('button', { name: 'Remove SMA 50' }).click();

  await expect(legendRow(page, 'SMA 50')).toHaveCount(0);
  await expect.poll(() => countColorPixels(page, LIGHT_COLOR_1)).toBeLessThan(LINE_PIXELS);
});

test('a theme change gives the lines the other palette without a new chart', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'light' });
  await openChart(page);
  const row = await addSma(page);
  // Light palette color 1: Purple 70.
  await expect(row.locator('.legend-value')).toHaveCSS('color', 'rgb(105, 41, 196)');
  const chartTable = page.getByRole('img', { name: CHART_NAME }).locator('table').first();
  await chartTable.evaluate((element) => {
    element.setAttribute('data-test-first-chart', '');
  });
  await expect.poll(() => countColorPixels(page, LIGHT_COLOR_1)).toBeGreaterThan(LINE_PIXELS);

  const header = page.getByRole('banner');
  await header.getByRole('button', { name: 'Theme: System' }).click();
  await header.getByRole('button', { name: 'Theme: Light' }).click();
  await expect(header.getByRole('button', { name: 'Theme: Dark' })).toBeVisible();

  // Dark palette color 1: Purple 60.
  await expect(row.locator('.legend-value')).toHaveCSS('color', 'rgb(138, 63, 252)');
  await expect(page.getByRole('img', { name: CHART_NAME }).locator('table[data-test-first-chart]')).toHaveCount(1);
  await expect.poll(() => countColorPixels(page, DARK_COLOR_1)).toBeGreaterThan(LINE_PIXELS);
  expect(await countColorPixels(page, LIGHT_COLOR_1)).toBeLessThan(LINE_PIXELS);
});

// The saved chart indicator set (section 23.9.7) and the favorites of Add indicator (section 23.9.5).

const OTHER_PAGE_PATH = '/instruments/NASDAQ/AAPL?currency=USD&bar_period=1-DAY';
// Magenta 70 of the light palette.
const MAGENTA_70_RGB = 'rgb(159, 24, 83)';

/** The legend names of each pane, from the top pane to the bottom pane. */
async function readLegendNames(page: Page): Promise<string[][]> {
  const legends = page.getByRole('list', { name: 'Legend' });
  await expect(legends.first().getByRole('listitem').first()).toBeVisible();
  const names: string[][] = [];
  for (const legend of await legends.all()) {
    const top = await readTop(legend);
    names.push([String(top), ...(await legend.locator('.legend-name').allTextContents())]);
  }
  return names
    .toSorted((first, second) => Number(first[0]) - Number(second[0]))
    .map((paneNames) => paneNames.slice(1));
}

/** The indicator keys of each saved pane. */
function readSavedPanes(localSet: LocalChartIndicatorSet): string[][] {
  const savedSet = localSet.read() as { panes: { indicators: { indicator: string }[] }[] };
  return savedSet.panes.map((pane) => pane.indicators.map((indicator) => indicator.indicator));
}

async function expectSavedChart(page: Page): Promise<void> {
  await expect.poll(() => readLegendNames(page)).toEqual([['SMA 50'], ['MACD 12 26 9'], ['RSI 14']]);
  await expect(legendRow(page, 'RSI 14').locator('.legend-value')).toHaveCSS('color', MAGENTA_70_RGB);
}

test('the indicators, the RSI color, and the pane order stay after a page load and on another instrument', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'light' });
  await openChart(page);
  await addSma(page);
  await addIndicator(page, /^RSI$/);
  await addIndicator(page, /^MACD$/);
  const row = await hoverRow(page, 'RSI 14');
  await row.getByRole('button', { name: 'Settings for RSI 14' }).click();
  const settings = page.getByRole('dialog', { name: 'RSI' });
  await settings.getByRole('group', { name: 'Line' }).getByRole('radio', { name: 'Magenta 70' }).check();
  await settings.getByRole('button', { name: 'Apply' }).click();
  await expect(settings).toBeHidden();
  await choosePaneOption(page, 'MACD 12 26 9', 'Move up');
  await expectSavedChart(page);
  await expect.poll(() => readSavedPanes(chartIndicatorSet)).toEqual([['sma'], ['macd'], ['rsi']]);

  await page.reload();
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('1096 bars');

  await expectSavedChart(page);

  await page.goto(OTHER_PAGE_PATH);
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText(/^\d+ bars$/);

  await expectSavedChart(page);
});

test('a star puts RSI first in Add indicator without an add, and the favorite stays after a page load', async ({ page }) => {
  await openChart(page);
  await page.getByRole('button', { name: 'Add indicator' }).click();
  const dialog = page.getByRole('dialog', { name: 'Add indicator' });
  await expect(dialog.getByRole('option').first()).toHaveText('SMA');

  await dialog.getByRole('button', { name: 'Add RSI to favorite indicators' }).click();

  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole('option').first()).toHaveText('RSI');
  await expect(dialog.getByRole('button', { name: 'Remove RSI from favorite indicators' })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('list', { name: 'Legend' }).getByRole('listitem')).toHaveCount(1);
  await expect.poll(() => (chartIndicatorSet.read() as { favorites: string[] }).favorites).toEqual(['rsi']);

  await page.reload();
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('1096 bars');
  await page.getByRole('button', { name: 'Add indicator' }).click();

  await expect(dialog.getByRole('option').first()).toHaveText('RSI');
  await expect(dialog.getByRole('button', { name: 'Remove RSI from favorite indicators' })).toBeVisible();
});

test('a failed save shows the detail text over the chart, and the chart keeps the change', async ({ page }) => {
  await page.route('**/api/market-data/chart-indicators', async (route) => {
    if (route.request().method() === 'PUT') {
      await route.fulfill({ status: 500, json: { detail: 'The database is not reachable.' } });
    } else {
      await route.fallback();
    }
  });
  await openChart(page);

  await addSma(page);

  await expect(page.getByRole('alert').filter({ hasText: 'The database is not reachable.' })).toBeVisible();
  await expect(legendRow(page, 'SMA 50')).toBeVisible();
});
