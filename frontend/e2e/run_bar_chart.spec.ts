// The bar chart of a backtest and of a forward test with the strategy indicators (docs/architecture/indicator.md
// section 23.9.8). The e2e server has 45 saved daily bars of FTBAR / ARCA / USD from 2025-11-03 and a stopped forward
// test of the strategy "E2E chart indicators" on them. The strategy template has
// CHART_INDICATORS = [{"indicator": "sma", "parameters": {"period": "average_period"}}] with average_period 20.
import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

const BAR_COUNT_TEXT = '45 bars';
const STRATEGY_INDICATOR_NAME = 'SMA 20';
const NUMBER_PATTERN = /^\d{1,3}(,\d{3})*\.\d{2}$/;
const INSTRUMENT_PAGE_PATH = '/instruments/SEHK/700?currency=HKD&bar_period=1-DAY';

async function startBacktest(request: APIRequestContext, name: string): Promise<number> {
  // eslint-disable-next-line @typescript-eslint/naming-convention -- `data` is the request body option of Playwright.
  const strategy = (await (await request.post('/api/strategies', { data: { name } })).json()) as { id: number };
  const version = (await (await request.get(`/api/strategies/${String(strategy.id)}/versions/1`)).json()) as { id: number };
  const response = await request.post('/api/backtests', {
    // eslint-disable-next-line @typescript-eslint/naming-convention -- `data` is the request body option of Playwright.
    data: {
      strategy_version_id: version.id,
      symbol: 'FTBAR',
      exchange: 'ARCA',
      currency: 'USD',
      bar_period: '1-DAY',
      start_utc: '2025-11-03T00:00:00Z',
      end_utc: '2025-12-18T00:00:00Z',
      paper_capital_usd: '10000',
    },
  });
  expect(response.status()).toBe(201);
  return ((await response.json()) as { id: number }).id;
}

async function findChartIndicatorForwardTest(request: APIRequestContext): Promise<number> {
  const forwardTests = (await (await request.get('/api/forward-tests')).json()) as { id: number; strategy_name: string }[];
  const forwardTest = forwardTests.find((item) => item.strategy_name === 'E2E chart indicators');
  if (forwardTest === undefined) {
    throw new Error('The e2e server has no forward test of "E2E chart indicators".');
  }
  return forwardTest.id;
}

function legendRow(page: Page, name: RegExp | string): ReturnType<Page['getByRole']> {
  return page.getByRole('list', { name: 'Legend' }).getByRole('listitem').filter({ hasText: name });
}

/** "Bars" shows the bar chart with the strategy indicators, the address keeps it, and an added EMA is not saved. */
async function expectBarsWithStrategyIndicators(page: Page): Promise<void> {
  const switcher = page.getByRole('tablist', { name: 'Chart' });
  await expect(switcher.getByRole('tab', { name: 'Equity' })).toHaveAttribute('aria-selected', 'true');

  await switcher.getByRole('tab', { name: 'Bars' }).click();

  await expect(page).toHaveURL(/[?&]chart=bars(&|$)/);
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText(BAR_COUNT_TEXT);
  await expect(legendRow(page, STRATEGY_INDICATOR_NAME).locator('.legend-value')).toHaveText([NUMBER_PATTERN]);

  await page.reload();
  await expect(switcher.getByRole('tab', { name: 'Bars' })).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText(BAR_COUNT_TEXT);
  await expect(legendRow(page, STRATEGY_INDICATOR_NAME)).toBeVisible();

  await page.getByRole('button', { name: 'Add indicator' }).click();
  const dialog = page.getByRole('dialog', { name: 'Add indicator' });
  await dialog.getByRole('option', { name: /^EMA/ }).click();
  await expect(dialog).toBeHidden();
  await expect(legendRow(page, /^EMA \d+/)).toBeVisible();
  await expect(legendRow(page, STRATEGY_INDICATOR_NAME)).toBeVisible();

  await switcher.getByRole('tab', { name: 'Equity' }).click();
  await expect(page).not.toHaveURL(/chart=bars/);
  await expect(page.getByRole('list', { name: 'Legend' })).toHaveCount(0);

  // The chart of a backtest or forward test does not save its indicators: the instrument page has no EMA from here.
  await page.goto(INSTRUMENT_PAGE_PATH);
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('1096 bars');
  await expect(page.getByRole('list', { name: 'Legend' }).first()).toBeVisible();
  await expect(legendRow(page, /^EMA \d+/)).toHaveCount(0);
}

test('the backtest bar chart shows the strategy indicators and keeps "Bars" in the address', async ({ page, request }, currentTest) => {
  const backtestId = await startBacktest(request, `Run bar chart ${currentTest.project.name} ${String(Date.now())}`);

  await page.goto(`/backtests/${String(backtestId)}`);

  await expectBarsWithStrategyIndicators(page);
});

test('the forward test bar chart shows the strategy indicators and keeps "Bars" in the address', async ({ page, request }) => {
  const forwardTestId = await findChartIndicatorForwardTest(request);

  await page.goto(`/forward-tests/${String(forwardTestId)}`);

  await expectBarsWithStrategyIndicators(page);
});
