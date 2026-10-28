// Strategy workbench (#106): the results panel and the editor panel with the swap button, the panel buttons, and the
// toolbar icon buttons with their shortcuts. A backtest that ends opens in a new result tab. The e2e database is not
// cleared between tests and browser projects, so each strategy name is unique.
import { expect, test, type Locator, type Page, type TestInfo } from '@playwright/test';

// A real child process runs each backtest. The browser projects share one queue with concurrency 1.
const BACKTEST_TIMEOUT_MILLISECONDS = 60_000;
// The forward test socket pushes a change after a worker comparison (every 2 seconds) and a socket read.
const STATUS_TIMEOUT_MILLISECONDS = 15_000;
const KEY_METRIC_NAMES = ['Total return', 'Net profit (USD)', 'Max drawdown', 'Win rate', 'Trades', 'Final equity (USD)'];

function createUniqueName(currentTest: TestInfo, title: string): string {
  return `${title} ${currentTest.project.name} ${String(Date.now())}`;
}

async function createStrategy(page: Page, name: string): Promise<void> {
  await page.goto('/strategies');
  await page.getByRole('button', { name: 'New strategy' }).click();
  await page.getByLabel('Strategy name').fill(name);
  await page.getByRole('button', { name: 'Create strategy' }).click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(name);
  // The toolbar works when the editor has the code of the open version.
  await expect(page.getByRole('textbox', { name: 'Strategy code' })).toContainText('class MovingAverageStrategy(Strategy):');
}

// The shortcuts use Cmd on macOS and Ctrl elsewhere, like the code editor. The page reads the platform of the browser.
async function readShortcutModifier(page: Page): Promise<'Meta' | 'Control'> {
  return (await page.evaluate(() => /Mac|iPhone|iPad/.test(navigator.platform))) ? 'Meta' : 'Control';
}

async function readTop(locator: Locator): Promise<number> {
  const box = await locator.boundingBox();
  if (box === null) {
    throw new Error('The panel is not visible.');
  }
  return box.y;
}

async function expectNoPageScroll(page: Page): Promise<void> {
  const sizes = await page.evaluate(() => ({
    scrollHeight: document.documentElement.scrollHeight,
    clientHeight: document.documentElement.clientHeight,
  }));
  expect(sizes.scrollHeight).toBeLessThanOrEqual(sizes.clientHeight);
}

test('swaps the results and the editor, keeps the order after a reload, and sizes each panel', async ({ page }, currentTest) => {
  await createStrategy(page, createUniqueName(currentTest, 'Workbench'));
  const results = page.getByRole('region', { name: 'Results' });
  const editor = page.getByRole('region', { name: 'Editor' });
  await expect(editor.getByRole('tab', { name: 'strategy.py' })).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByRole('separator', { name: 'Resize the results and the editor' })).toBeVisible();
  expect(await readTop(results)).toBeLessThan(await readTop(editor));
  await expectNoPageScroll(page);

  await page.getByRole('button', { name: 'Put editor on top' }).click();
  expect(await readTop(editor)).toBeLessThan(await readTop(results));
  await page.reload();
  await expect(page.getByRole('button', { name: 'Put editor at bottom' })).toBeVisible();
  expect(await readTop(editor)).toBeLessThan(await readTop(results));

  // Maximize: the other panel shows only its tab line, and no splitter shows. Escape restores.
  await editor.getByRole('button', { name: 'Maximize panel' }).click();
  await expect(page.getByRole('separator')).toHaveCount(0);
  await expect(results.getByRole('button', { name: 'Minimize panel' })).toBeVisible();
  await expect(results.getByText('No backtests')).toBeHidden();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('separator', { name: 'Resize the results and the editor' })).toBeVisible();

  await results.getByRole('button', { name: 'Minimize panel' }).click();
  await expect(results.getByText('No backtests')).toBeHidden();
  await results.getByRole('button', { name: 'Restore panel' }).click();
  await expect(results.getByText('No backtests')).toBeVisible();
  await expectNoPageScroll(page);
});

test('names the shortcut of each toolbar button, and Ctrl S saves from the editor', async ({ page }, currentTest) => {
  const name = createUniqueName(currentTest, 'Shortcut');
  await createStrategy(page, name);
  const modifier = await readShortcutModifier(page);

  await expect(page.getByRole('button', { name: 'Save version', exact: true })).toHaveAttribute('aria-keyshortcuts', `${modifier}+S`);
  await expect(page.getByRole('button', { name: 'Run backtest' })).toHaveAttribute('aria-keyshortcuts', `${modifier}+B`);
  await expect(page.getByRole('button', { name: 'Start forward test' })).toHaveAttribute(
    'aria-keyshortcuts',
    `${modifier}+Shift+F`,
  );

  const code = page.getByRole('textbox', { name: 'Strategy code' });
  await code.click();
  await page.keyboard.press('End');
  await page.keyboard.insertText('\n# A comment.');
  await expect(page.getByRole('button', { name: 'Save version, unsaved changes' })).toBeVisible();
  await page.keyboard.press(`${modifier}+s`);

  await expect(page.getByRole('status').filter({ hasText: 'Saved' })).toHaveText(`Saved as ${name} v2.`);
  await expect(page.getByRole('combobox', { name: 'Version' })).toHaveText('v2');
  await expect(code).toBeFocused();
});

test('runs a backtest from the toolbar and opens its result in a new tab', async ({ page, request }, currentTest) => {
  test.setTimeout(BACKTEST_TIMEOUT_MILLISECONDS * 2);
  // The chart saves the daily bars from 2023-01-02 to 2026-01-01 in PostgreSQL. Backtests read only saved bars.
  await page.goto('/instruments/NASDAQ/AAPL?currency=USD&bar_period=1-DAY');
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('1096 bars');
  // The browser projects share one database: another project can add AAPL first (409).
  // eslint-disable-next-line @typescript-eslint/naming-convention -- `data` is the request body option of Playwright.
  const watchlistResponse = await request.post('/api/watchlist', { data: { symbol: 'AAPL', exchange: 'NASDAQ', currency: 'USD' } });
  expect([201, 409]).toContain(watchlistResponse.status());
  const name = createUniqueName(currentTest, 'Run');
  await createStrategy(page, name);

  await page.keyboard.press(`${await readShortcutModifier(page)}+b`);
  const dialog = page.getByRole('dialog', { name: 'New backtest' });
  // The dialog has the open strategy version.
  await expect(dialog.getByRole('combobox', { name: 'Strategy', exact: true })).toHaveText(name);
  await expect(dialog.getByRole('combobox', { name: 'Strategy version' })).toHaveText(`${name} v1`);
  await dialog.getByRole('combobox', { name: 'Bar period' }).click();
  await page.getByRole('option', { name: '1 day', exact: true }).click();
  await dialog.getByRole('combobox', { name: 'Instrument', exact: true }).click();
  await page.getByRole('option', { name: 'AAPL / NASDAQ / USD', exact: true }).click();
  await dialog.getByLabel('Start date (UTC)').fill('2023-01-02');
  await dialog.getByLabel('End date (UTC)').fill('2026-01-01');
  await dialog.getByRole('button', { name: 'Start backtest' }).click();
  await expect(dialog).toHaveCount(0);

  // A child process runs the backtest for some seconds. Meanwhile the user looks at another tab. The finished backtest
  // then opens in its own tab, with its number and total return.
  const results = page.getByRole('region', { name: 'Results' });
  const backtestTab = results.getByRole('tab', { name: /^Backtest #\d+/ });
  await expect(backtestTab).toBeVisible();
  // The list reads again every 2 seconds, so the running state shows at least until the next read.
  await expect(page.getByRole('button', { name: 'Backtest is running' })).toHaveAttribute('aria-disabled', 'true');
  await results.getByRole('tab', { name: 'Logs' }).click();
  await expect(backtestTab).toHaveText(/^Backtest #\d+\s+[+-]?[\d,]+\.\d{2} %$/, { timeout: BACKTEST_TIMEOUT_MILLISECONDS });
  await expect(backtestTab).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByRole('button', { name: 'Run backtest' })).toBeVisible();
  await expect(results.getByRole('term')).toHaveText(KEY_METRIC_NAMES);
  await expect(results.getByRole('img', { name: 'Equity and drawdown' }).locator('canvas').first()).toBeVisible();
  await expect(results.getByRole('link', { name: 'TradingView', exact: true })).toBeVisible();

  await results.getByRole('tab', { name: 'Trades' }).click();
  await expect(results.getByRole('scrollbar', { name: 'Trades scroll bar' })).toBeVisible();
  await results.getByRole('tab', { name: 'Orders' }).click();
  await expect(results).toContainText('No orders');
  await expectNoPageScroll(page);
});

test('starts a forward test from the toolbar and stops it with the same button', async ({ page }, currentTest) => {
  const name = createUniqueName(currentTest, 'Signal');
  const uniqueNumber = String(Date.now() % 1_000_000);
  await createStrategy(page, name);
  const modifier = await readShortcutModifier(page);

  await page.keyboard.press(`${modifier}+Shift+F`);
  const dialog = page.getByRole('dialog', { name: `Start forward test of ${name} v1` });
  await dialog.getByLabel('Symbol').fill(`SW${currentTest.project.name.slice(0, 2).toUpperCase()}${uniqueNumber}`);
  await dialog.getByLabel('Exchange').fill('ARCA');
  await dialog.getByRole('combobox', { name: 'Bar period' }).click();
  await page.getByRole('option', { name: '1 minute', exact: true }).click();
  // A local time far after the fixed clock of the e2e server, so the worker does not stop the forward test.
  await dialog.getByLabel('End time (local, optional)').fill('2099-12-31T23:30');
  await dialog.getByRole('button', { name: 'Start forward test' }).click();
  await expect(dialog).toHaveCount(0);

  const stopButton = page.getByRole('button', { name: 'Stop forward test', exact: true });
  await expect(stopButton).toBeVisible({ timeout: STATUS_TIMEOUT_MILLISECONDS });
  await stopButton.click();
  await expect(page.getByRole('button', { name: 'Start forward test', exact: true })).toBeVisible({
    timeout: STATUS_TIMEOUT_MILLISECONDS,
  });
});
