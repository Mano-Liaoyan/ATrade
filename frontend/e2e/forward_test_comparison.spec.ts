// A forward test compared with a backtest of the same period (docs/architecture/forward_test.md section 12.10).
// backend/tests/e2e_server.py adds the stopped forward test "E2E compared forward test" on FTCMP / ARCA with a start
// balance, 40 fills, equity points, 1 interruption, and the saved daily bars of its period. The forward test never runs:
// the child start function of the e2e server is a fake. The backtest runs in a real child process.
import { expect, test } from '@playwright/test';

// A real child process runs each backtest. The browser projects share one queue.
const BACKTEST_TIMEOUT_MILLISECONDS = 90_000;
const COMPARED_STRATEGY_LABEL = 'E2E compared forward test v1';

test('backtests the same period and compares the metrics, the equity curves, and the fills', async ({ page }) => {
  test.setTimeout(BACKTEST_TIMEOUT_MILLISECONDS * 2);
  await page.setViewportSize({ width: 1280, height: 640 });
  await page.goto('/forward-tests');

  const row = page.getByRole('region', { name: 'Forward tests' }).getByRole('row', { name: /FTCMP/ });
  await row.getByRole('button', { name: /^Actions for forward test \d+$/ }).click();
  await page.getByRole('menuitem', { name: 'Backtest the same period' }).click();

  await expect(page).toHaveURL(/\/forward-tests\/\d+\/comparison\/\d+$/);
  await expect(page.getByRole('status', { name: 'Backtest status' })).toContainText('Finished', {
    timeout: BACKTEST_TIMEOUT_MILLISECONDS,
  });

  const metrics = page.getByRole('region', { name: 'Compared metrics' });
  await expect(metrics.getByRole('columnheader', { name: new RegExp(COMPARED_STRATEGY_LABEL) })).toBeVisible();
  await expect(metrics.getByRole('columnheader', { name: /^Backtest #\d+$/ })).toBeVisible();
  // The forward test records 40 fills. The bar count strategy of the backtest buys and sells 3 times.
  await expect(metrics.getByRole('row', { name: /^Trades/ })).toHaveText(/Trades\s*40\s*3/);
  await expect(page.getByRole('img', { name: 'Compared equity curves' })).toBeVisible();
  await expect(page.getByRole('list', { name: 'Compared equity curves interruptions' }).getByRole('listitem')).toHaveText([
    'Interrupted from 2026-03-21 01:00:00 UTC to 2026-03-24 01:00:00 UTC',
  ]);

  const fills = page.getByRole('region', { name: 'Compared fills' });
  const firstFill = fills.getByRole('row', { name: /2026-03-03 00:00:00 UTC/ });
  await expect(firstFill).toContainText('BUY');
  await expect(firstFill).toContainText('101.01');

  const track = page.getByRole('scrollbar', { name: 'Compared fills scroll bar' });
  const lastRow = fills.getByRole('row').last();
  await fills.scrollIntoViewIfNeeded();
  await expect(track).toBeVisible();
  await expect(track.locator('.scroll-thumb')).toBeVisible();
  await expect(lastRow).not.toBeInViewport();

  await track.focus();
  await page.keyboard.press('End');

  await expect(lastRow).toBeInViewport();
  await expect(track).toHaveAttribute('aria-valuenow', '100');

  // The forward test page links to the comparison with this backtest.
  const comparisonUrl = page.url();
  const backtestId = comparisonUrl.split('/').at(-1) ?? '';
  await page.goto('/forward-tests');
  await row.getByRole('link', { name: /^#\d+$/ }).click();
  await expect(page).toHaveURL(/\/forward-tests\/\d+$/);
  const setup = page.getByRole('definition');
  await expect(setup.filter({ hasText: 'E2E compared forward test v1' })).toBeVisible();
  await expect(setup.filter({ hasText: /^1 day$/ })).toBeVisible();
  await expect(setup.filter({ hasText: /^10,000\.00$/ })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Interruptions' }).getByRole('row')).toHaveCount(2);
  await expect(page.getByRole('img', { name: 'Forward test equity curve' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Forward test fills' })).toBeVisible();
  await page.getByRole('link', { name: `Compare with backtest #${backtestId}`, exact: true }).click();
  await expect(page).toHaveURL(comparisonUrl);
});
