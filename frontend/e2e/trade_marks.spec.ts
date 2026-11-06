// The trade marks of the backtest and forward test bar charts and their link with the Trades and Fills tables
// (docs/architecture/indicator.md section 23.9.9). The e2e server has 45 saved daily bars of FTBAR / ARCA / USD from
// 2025-11-03 (close 100 + |(n + 10) mod 20 − 10| for bar n), the finished backtest of "E2E trade marks" with 5 trades
// at the bar ends (1 USD commission each), and the stopped forward test of "E2E chart indicators" with 2 fills.
import { expect, test, type APIRequestContext, type Locator, type Page } from '@playwright/test';

// The key metric tiles wrap at this width, so the bar chart is short. At 720 pixels the legend lies over the marks.
test.use({ viewport: { width: 1280, height: 900 } });

// The marks read the place of each mark from the series primitive (the "Trade marks" list of TradeMarkLayer).
function markItems(page: Page): Locator {
  return page.getByRole('list', { name: 'Trade marks' }).getByRole('listitem');
}

async function findRunId(request: APIRequestContext, path: string, strategyName: string): Promise<number> {
  const runs = (await (await request.get(path)).json()) as { id: number; strategy_name: string }[];
  const run = runs.find((item) => item.strategy_name === strategyName);
  if (run === undefined) {
    throw new Error(`The e2e server has no run of "${strategyName}".`);
  }
  return run.id;
}

/** Row n (from 1) of the Trades or Fills table: the row header cell has the number. */
function tableRow(page: Page, table: 'Trades' | 'Fills', number: number): Locator {
  return page
    .getByRole('region', { name: table })
    .getByRole('row')
    .filter({ has: page.getByRole('rowheader', { name: String(number), exact: true }) });
}

async function readMarkPoint(mark: Locator): Promise<{ x: number; y: number }> {
  return { x: Number(await mark.getAttribute('data-x')), y: Number(await mark.getAttribute('data-y')) };
}

/** The chart scrolled so that the mark is in the center of the plot (the width of the price pane overlay). */
async function expectInCenter(page: Page, mark: Locator): Promise<void> {
  const plot = await page.locator('.pane-overlay').first().boundingBox();
  expect(plot).not.toBeNull();
  const plotWidth = plot?.width ?? 0;
  await expect.poll(async () => Math.abs((await readMarkPoint(mark)).x - plotWidth / 2)).toBeLessThan(plotWidth / 20);
}

/** Moves the pointer onto the mark until its tooltip shows: the price scale can change when the series arrive. */
async function hoverMark(page: Page, mark: Locator): Promise<void> {
  await expect(async () => {
    const canvas = await page.locator('.chart-canvas').boundingBox();
    const point = await readMarkPoint(mark);
    await page.mouse.move(0, 0);
    await page.mouse.move((canvas?.x ?? 0) + point.x, (canvas?.y ?? 0) + point.y);
    await expect(page.getByRole('tooltip')).toBeVisible({ timeout: 1000 });
  }).toPass();
}

test('the backtest bar chart shows a mark for each bar and side, with a tooltip, linked to the Trades rows', async ({ page, request }) => {
  const backtestId = await findRunId(request, '/api/backtests', 'E2E trade marks');
  await page.goto(`/backtests/${String(backtestId)}`);
  await expect(page.getByRole('tab', { name: 'Equity' })).toHaveAttribute('aria-selected', 'true');

  // A click on a Trades row in "Equity" shows "Bars" and scrolls to the bar of the trade.
  await tableRow(page, 'Trades', 2).getByRole('cell').first().click();

  await expect(page).toHaveURL(/[?&]chart=bars(&|$)/);
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('45 bars');
  // The 2 sells of bar 38 are one mark. The trade that ends a round trip has its net profit after commissions.
  await expect(markItems(page)).toHaveText([
    'Buy 10 @ 105.00',
    'Sell 10 @ 108.00 +28.00',
    'Buy 10 @ 110.00',
    'Sell 5 @ 102.00; Sell 5 @ 102.00 −83.00',
  ]);
  await expect(markItems(page).nth(0)).toHaveAttribute('data-side', 'BUY');
  await expect(markItems(page).nth(1)).toHaveAttribute('data-side', 'SELL');
  await expect(tableRow(page, 'Trades', 2)).toHaveAttribute('aria-current', 'true');
  // The mark of the selected row keeps the focus ring.
  await expect(markItems(page).nth(1)).toHaveAttribute('data-ring', 'true');
  await expectInCenter(page, markItems(page).nth(1));

  // The pointer on a mark shows the tooltip, one line for each trade.
  await hoverMark(page, markItems(page).nth(1));
  const tooltip = page.getByRole('tooltip');
  await expect(tooltip).toContainText('Sell 10 @ 108.00');
  await expect(tooltip.locator('.trade-profit--success')).toHaveText('+28.00');

  // The pointer on a row gives its mark the focus ring.
  await page.mouse.move(0, 0);
  await expect(tooltip).toBeHidden();
  await expect(markItems(page).nth(0)).toHaveAttribute('data-ring', 'false');
  await tableRow(page, 'Trades', 1).hover();
  await expect(markItems(page).nth(0)).toHaveAttribute('data-ring', 'true');

  // The row itself takes the focus with Tab, shows the Carbon focus, and Enter selects it and scrolls to its bar.
  await page.mouse.move(0, 0);
  await tableRow(page, 'Trades', 4).focus();
  await page.keyboard.press('Tab');
  await expect(tableRow(page, 'Trades', 5)).toBeFocused();
  await expect(tableRow(page, 'Trades', 5).getByRole('cell').first()).toHaveCSS('box-shadow', /inset/);
  await expect(markItems(page).nth(3)).toHaveAttribute('data-ring', 'true');
  await page.keyboard.press('Enter');
  await expect(tableRow(page, 'Trades', 5)).toHaveAttribute('aria-current', 'true');
  await expect(tableRow(page, 'Trades', 2)).not.toHaveAttribute('aria-current', 'true');
  await expectInCenter(page, markItems(page).nth(3));
  await hoverMark(page, markItems(page).nth(3));
  await expect(tooltip.locator('.trade-line')).toHaveCount(2);
  await expect(tooltip.locator('.trade-profit--error')).toHaveText('−83.00');
});

test('the forward test bar chart shows a mark for each fill, linked to the Fills rows', async ({ page, request }) => {
  const forwardTestId = await findRunId(request, '/api/forward-tests', 'E2E chart indicators');
  await page.goto(`/forward-tests/${String(forwardTestId)}`);
  await expect(page.getByRole('tab', { name: 'Equity' })).toHaveAttribute('aria-selected', 'true');

  await tableRow(page, 'Fills', 2).getByRole('cell').first().click();

  await expect(page).toHaveURL(/[?&]chart=bars(&|$)/);
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('45 bars');
  // Each fill is 1 second after a bar end: it is on the next bar.
  await expect(markItems(page)).toHaveText(['Buy 1 @ 108.01', 'Sell 1 @ 105.01 −3.00']);
  await expect(markItems(page).nth(1)).toHaveAttribute('data-ring', 'true');
  await expectInCenter(page, markItems(page).nth(1));

  // The centered mark: the legend rows at the top left can cover a mark near them.
  await hoverMark(page, markItems(page).nth(1));
  await expect(page.getByRole('tooltip')).toContainText('Sell 1 @ 105.01');
  await expect(page.getByRole('tooltip').locator('.trade-profit--error')).toHaveText('−3.00');
  await page.mouse.move(0, 0);
  await tableRow(page, 'Fills', 1).hover();
  await expect(markItems(page).nth(0)).toHaveAttribute('data-ring', 'true');
});
