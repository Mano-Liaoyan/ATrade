// The backtest tabs of the strategy results panel: many backtest tabs scroll in their own strip with a visible track,
// and Trades, Orders, and Logs stay visible. Each backtest tab has a status icon in front of its name and no status
// word. A closed tab stays closed after a reload, and the "Closed backtests" menu opens it again. A failed backtest tab shows its error at once: the last error line,
// "Ask AI to fix", and the full log. The backtest routes are faked here, so no backtest runs.
import { expect, test, type Page, type TestInfo } from '@playwright/test';

const BACKTEST_COUNT = 22;
const FAILED_BACKTEST_ID = 21;
const LAST_ERROR_LINE = "AttributeError: 'MovingAverageStrategy' object has no attribute 'id'";
const TRACEBACK = [
  'Traceback (most recent call last):',
  '  File "/tmp/atrade-bt-21/strategy.py", line 42, in on_start',
  '    self.log.info(f"Start {self.id}")',
  LAST_ERROR_LINE,
  '',
].join('\n');

function createUniqueName(currentTest: TestInfo, title: string): string {
  return `${title} ${currentTest.project.name} ${String(Date.now())}`;
}

function fakeBacktest(id: number, strategyId: number, count: number): Record<string, unknown> {
  // The newest backtest runs, #21 failed, and the older backtests finished.
  const status = id === count ? 'running' : id === FAILED_BACKTEST_ID ? 'failed' : 'finished';
  return {
    id,
    strategy_id: strategyId,
    status,
    error_message: status === 'failed' ? TRACEBACK : null,
    metrics: status === 'finished' ? { total_return_percent: String(id / 10) } : null,
  };
}

async function openStrategyWithFakeBacktests(page: Page, currentTest: TestInfo, count = BACKTEST_COUNT): Promise<void> {
  await page.goto('/strategies');
  await page.getByRole('button', { name: 'New strategy' }).click();
  const name = createUniqueName(currentTest, 'Tabs');
  await page.getByLabel('Strategy name').fill(name);
  await page.getByRole('button', { name: 'Create strategy' }).click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(name);
  await expect(page).toHaveURL(/\/strategies\/\d+$/);
  await expect(page.getByRole('textbox', { name: 'Strategy code' })).toContainText('class MovingAverageStrategy(Strategy):');
  const strategyId = Number(page.url().split('/').at(-1));
  const backtests = Array.from({ length: count }, (_, index) => fakeBacktest(count - index, strategyId, count));
  await page.route('**/api/backtests', async (route) => {
    await route.fulfill({ json: backtests });
  });
  await page.route(/\/api\/backtests\/\d+$/, async (route) => {
    const id = Number(route.request().url().split('/').at(-1));
    await route.fulfill({ json: { ...fakeBacktest(id, strategyId, count), trades: [], equity_curve: [] } });
  });
  await page.reload();
}

test('many backtest tabs scroll in their own strip and Trades, Orders, and Logs stay visible', async ({ page }, currentTest) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await openStrategyWithFakeBacktests(page, currentTest);
  const results = page.getByRole('region', { name: 'Results' });

  await expect(results.getByRole('tab', { name: /Backtest #\d+/ })).toHaveCount(BACKTEST_COUNT);
  for (const name of ['Trades', 'Orders', 'Logs']) {
    await expect(results.getByRole('tab', { name, exact: true })).toBeInViewport({ ratio: 1 });
  }
  const track = results.getByRole('scrollbar', { name: 'Results scroll bar' });
  await expect(track).toBeVisible();
  await expect(track.locator('.scroll-thumb')).toBeVisible();
  const oldestTab = results.getByRole('tab', { name: 'Finished Backtest #1 +0.10 %' });
  await expect(oldestTab).not.toBeInViewport({ ratio: 1 });
  await track.focus();
  await page.keyboard.press('End');
  await expect(oldestTab).toBeInViewport({ ratio: 1 });
  // Backtest #22 runs, so the page checks the backtest list again. The strip stays where the user scrolled it.
  await page.waitForResponse('**/api/backtests');
  // Two animation frames, so the page shows the new list before the check.
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  await expect(oldestTab).toBeInViewport({ ratio: 1 });

  // The status icon is in front of the name. The tab text has no status word.
  await expect(results.getByRole('tab', { name: 'Running Backtest #22' })).toHaveText('Backtest #22');
  await expect(results.getByRole('tab', { name: 'Failed Backtest #21' })).toHaveText('Backtest #21');
});

test('a failed backtest tab shows its error, and a closed tab stays closed after a reload', async ({ page }, currentTest) => {
  await openStrategyWithFakeBacktests(page, currentTest);
  const results = page.getByRole('region', { name: 'Results' });
  const failedTab = results.getByRole('tab', { name: 'Failed Backtest #21' });

  await failedTab.click();
  await expect(results.getByRole('alert').filter({ hasText: LAST_ERROR_LINE })).toContainText('Failed');
  await expect(results.getByRole('region', { name: 'Log' })).toContainText('in on_start');
  await results.getByRole('button', { name: 'Ask AI to fix' }).click();
  // Without an open conversation, the request stays in the message input of the AI assistant.
  await expect(page.getByRole('textbox', { name: 'Message' })).toHaveValue(
    'Backtest #21 failed. Read it with read_backtest and fix the strategy code.',
  );

  await results.getByRole('button', { name: 'Close Backtest #21' }).click();
  await expect(failedTab).toHaveCount(0);
  await expect(results.getByRole('tab', { name: 'Running Backtest #22' })).toHaveAttribute('aria-selected', 'true');
  await page.reload();
  await expect(results.getByRole('tab', { name: 'Running Backtest #22' })).toBeVisible();
  await expect(failedTab).toHaveCount(0);
});

test('closed backtest tabs open again from the "Closed backtests" menu', async ({ page }, currentTest) => {
  await openStrategyWithFakeBacktests(page, currentTest, 3);
  const results = page.getByRole('region', { name: 'Results' });
  const backtestTabs = results.getByRole('tab', { name: /Backtest #\d+/ });
  const reopenButton = results.getByRole('button', { name: 'Closed backtests' });
  await expect(backtestTabs).toHaveCount(3);
  await expect(reopenButton).toHaveCount(0);

  for (const name of ['Backtest #3', 'Backtest #2', 'Backtest #1']) {
    await results.getByRole('button', { name: new RegExp(`^Close ${name}\\b`) }).click();
  }
  await expect(backtestTabs).toHaveCount(0);
  await expect(results.getByText('No open backtests', { exact: true })).toBeVisible();
  await expect(reopenButton).toBeVisible();

  // The menu lists the closed backtests the newest first, like their tabs, then "Reopen all". The keyboard opens it and
  // picks an item. The reopened tab is selected and has the focus.
  await reopenButton.focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('menuitem')).toHaveText(['Backtest #3', 'Backtest #2 +0.20 %', 'Backtest #1 +0.10 %', 'Reopen all']);
  await expect(page.getByRole('menuitem', { name: 'Running Backtest #3' })).toBeFocused();
  await expect(page.getByRole('menuitem', { name: 'Finished Backtest #2 +0.20 %' })).toBeVisible();
  await page.keyboard.press('ArrowDown');
  await expect(page.getByRole('menuitem', { name: /Backtest #2/ })).toBeFocused();
  await page.keyboard.press('Enter');
  const secondTab = results.getByRole('tab', { name: /Backtest #2/ });
  await expect(secondTab).toHaveAttribute('aria-selected', 'true');
  await expect(secondTab).toBeFocused();
  await expect(backtestTabs).toHaveCount(1);

  // The closed list stays after a reload. "Reopen all" opens every closed tab, and the button goes.
  await page.reload();
  await expect(backtestTabs).toHaveCount(1);
  await reopenButton.click();
  await page.getByRole('menuitem', { name: 'Reopen all' }).click();
  await expect(backtestTabs).toHaveCount(3);
  await expect(reopenButton).toHaveCount(0);
  await page.reload();
  await expect(backtestTabs).toHaveCount(3);
});
