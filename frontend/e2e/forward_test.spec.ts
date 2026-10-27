// Forward tests with the fake child start function of backend/tests/e2e_server.py: the worker runs in the e2e server,
// and each fake child stops at once after the stop request. The server has 30 stopped forward tests of the strategy
// "E2E stopped forward tests", so the list overflows. The client ID range 10-13 allows 4 forward tests at a time, and
// the browser projects run at the same time, so each test starts only 1 forward test and stops it.
import { expect, test, type Locator, type Page } from '@playwright/test';

// The stop takes 2 worker comparisons (stopping, then stopped) and 1 socket read, each every 2 seconds. A backtest
// child of another test can slow the server, so the wait is longer than the default 5 seconds.
const STOP_TIMEOUT_MILLISECONDS = 15_000;

async function createStrategy(page: Page, strategyName: string): Promise<void> {
  await page.goto('/strategies');
  await page.getByLabel('Strategy name').fill(strategyName);
  await page.getByRole('button', { name: 'Create strategy' }).click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(strategyName);
}

test('starts a forward test, sees it running in the list, and stops it', async ({ page }, currentTest) => {
  // The e2e database is not cleared between tests and browser projects, so the names are unique.
  const uniqueNumber = String(Date.now() % 1_000_000);
  const strategyName = `Forward test ${currentTest.project.name} ${uniqueNumber}`;
  const symbol = `FT${currentTest.project.name.slice(0, 2).toUpperCase()}${uniqueNumber}`;
  await createStrategy(page, strategyName);

  await page.getByRole('link', { name: 'Forward tests' }).click();
  await page.getByLabel('Strategy', { exact: true }).selectOption({ label: strategyName });
  await expect(page.getByLabel('Strategy version')).toHaveValue(/\d+/);
  await expect(page.getByRole('region', { name: 'Latest backtest result' })).toHaveText('no backtest result');
  await page.getByLabel('Symbol').fill(symbol);
  await page.getByLabel('Exchange').fill('ARCA');
  await page.getByLabel('Bar period').selectOption('1-MINUTE');
  // A local time far after the fixed clock of the e2e server, so the worker does not stop the forward test.
  await page.getByLabel('End time (local, optional)').fill('2099-12-31T23:30');
  await page.getByRole('button', { name: 'Start forward test' }).click();

  const forwardTests = page.getByRole('region', { name: 'Forward tests' });
  const row = forwardTests.getByRole('row', { name: new RegExp(symbol) });
  await expect(row).toContainText(`${strategyName} v1`);
  await expect(row).toContainText('1 min');
  await expect(row).toContainText('2026-01-02 03:04:05 UTC');
  // The browser sent UTC and shows the end time in its own time zone again.
  await expect(row).toContainText('2099-12-31 23:30');
  // The worker compares the states every 2 seconds and the socket pushes the change.
  await expect(row).toContainText('Running');
  const forwardTestNumber = (await row.getByRole('rowheader').textContent())?.trim() ?? '';

  // The order form does not send a paper order by hand on the instrument of the running forward test, and says why.
  await page.getByRole('link', { name: 'Home' }).click();
  const ticket = page.getByRole('form', { name: 'Paper order' });
  await ticket.getByLabel('Order symbol').fill(symbol);
  await ticket.getByLabel('Exchange').fill('ARCA');
  const reviewButton = ticket.getByRole('button', { name: 'Review order' });
  await expect(reviewButton).toBeDisabled();
  await expect(reviewButton).toHaveAccessibleDescription(
    `Forward test ${forwardTestNumber.replace('#', '')} (${strategyName} v1) trades ${symbol} / ARCA. Stop the forward test to send an order by hand.`,
  );

  await page.getByRole('link', { name: 'Forward tests' }).click();
  await row.getByRole('button', { name: /Stop forward test/ }).click();

  await expect(row).toContainText('Stopped', { timeout: STOP_TIMEOUT_MILLISECONDS });
  await expect(row.getByRole('button', { name: /Stop forward test/ })).toHaveCount(0);
});

test('the forward test list has a visible scroll track', async ({ page }) => {
  await page.goto('/forward-tests');

  const forwardTests = page.getByRole('region', { name: 'Forward tests' });
  const track = page.getByRole('scrollbar', { name: 'Forward tests scroll bar' });
  const lastRow = forwardTests.getByRole('row').last();
  await forwardTests.scrollIntoViewIfNeeded();
  await expect(track).toBeVisible();
  await expect(track.locator('.scroll-thumb')).toBeVisible();
  await expect(lastRow).not.toBeInViewport();

  await track.focus();
  await page.keyboard.press('End');

  await expect(lastRow).toBeInViewport();
  await expect(track).toHaveAttribute('aria-valuenow', '100');
});

/** The words of the element text that the browser breaks over 2 lines or more. */
async function findBrokenWords(element: Locator): Promise<string[]> {
  return element.evaluate((root) => {
    const brokenWords: string[] = [];
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node !== null; node = walker.nextNode()) {
      for (const match of (node.textContent ?? '').matchAll(/\S+/g)) {
        const range = document.createRange();
        range.setStart(node, match.index);
        range.setEnd(node, match.index + match[0].length);
        const lineTops = new Set(Array.from(range.getClientRects(), (rect) => Math.round(rect.top)));
        if (lineTops.size > 1) {
          brokenWords.push(match[0]);
        }
      }
    }
    return brokenWords;
  });
}

test('at 1024 pixels the column names of the forward test list break only between words', async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 768 });
  await page.goto('/forward-tests');

  const forwardTests = page.getByRole('region', { name: 'Forward tests' });
  const columnHeaders = forwardTests.getByRole('columnheader');
  await expect(columnHeaders.first()).toBeVisible();
  for (const columnHeader of await columnHeaders.all()) {
    expect(await findBrokenWords(columnHeader)).toEqual([]);
  }
  // The table is not wider than its region, so no column is out of reach.
  expect(await forwardTests.evaluate((region) => region.scrollWidth <= region.clientWidth)).toBe(true);
});
