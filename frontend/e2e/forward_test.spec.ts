// Forward test workbench (#105) with the fake child start function of backend/tests/e2e_server.py: the worker runs in the e2e server,
// and each fake child stops at once after the stop request. The server has 30 stopped forward tests of the strategy
// "E2E stopped forward tests", so the list overflows. The client ID range 10-13 allows 4 forward tests at a time, and
// the browser projects run at the same time, so each test starts only 1 forward test and stops it.
import { expect, test, type Locator, type Page } from '@playwright/test';

// A status change takes worker comparisons and socket reads, each every 2 seconds: "Running" takes 1 comparison and
// 1 read (up to 4 seconds), "Stopped" takes 2 comparisons and 1 read. The worker and the socket run in the e2e server
// process, and the backtest children of other tests slow it, so the waits are longer than the default 5 seconds.
const STATUS_TIMEOUT_MILLISECONDS = 15_000;
// The start and stop test waits for 5 server cycles (Running in the header and in the list, the order block, Stopped in
// the header and in the list). Each can take up to STATUS_TIMEOUT_MILLISECONDS under the load of the full suite, so the
// default test timeout of 30 seconds ended the test while the list still waited for its socket message.
test.describe.configure({ timeout: STATUS_TIMEOUT_MILLISECONDS * 4 });

async function createStrategy(page: Page, strategyName: string): Promise<void> {
  await page.goto('/strategies');
  await page.getByRole('button', { name: 'New strategy' }).click();
  await page.getByLabel('Strategy name').fill(strategyName);
  await page.getByRole('button', { name: 'Create strategy' }).click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(strategyName);
}

async function expectNoPageScroll(page: Page): Promise<void> {
  const sizes = await page.evaluate(() => ({
    scrollHeight: document.documentElement.scrollHeight,
    clientHeight: document.documentElement.clientHeight,
  }));
  expect(sizes.scrollHeight).toBeLessThanOrEqual(sizes.clientHeight);
}

test('starts a forward test in the New forward test dialog, sees it running, and stops it from the header line', async ({
  page,
}, currentTest) => {
  // The e2e database is not cleared between tests and browser projects, so the names are unique.
  const uniqueNumber = String(Date.now() % 1_000_000);
  const strategyName = `Forward test ${currentTest.project.name} ${uniqueNumber}`;
  const symbol = `FT${currentTest.project.name.slice(0, 2).toUpperCase()}${uniqueNumber}`;
  await createStrategy(page, strategyName);

  await page.getByRole('link', { name: 'Forward tests', exact: true }).click();
  await page.getByRole('button', { name: 'New forward test' }).click();
  const dialog = page.getByRole('dialog', { name: 'New forward test' });
  await dialog.getByRole('combobox', { name: 'Strategy', exact: true }).click();
  await page.getByRole('option', { name: strategyName }).click();
  await expect(dialog.getByRole('combobox', { name: 'Strategy version' })).toHaveText(`${strategyName} v1`);
  await expect(dialog.getByRole('region', { name: 'Latest backtest result' })).toHaveText('no backtest result');
  await dialog.getByLabel('Symbol').fill(symbol);
  await dialog.getByLabel('Exchange').fill('ARCA');
  await dialog.getByRole('combobox', { name: 'Bar period' }).click();
  await page.getByRole('option', { name: '1 minute', exact: true }).click();
  // A local time far after the fixed clock of the e2e server, so the worker does not stop the forward test.
  await dialog.getByLabel('End time (local, optional)').fill('2099-12-31T23:30');
  await dialog.getByRole('button', { name: 'Start forward test' }).click();

  // The page opens the new forward test.
  await expect(dialog).toHaveCount(0);
  await expect(page).toHaveURL(/\/forward-tests\/\d+$/);
  const forwardTestId = page.url().split('/').at(-1) ?? '';
  const chartPanel = page.getByRole('region', { name: `Forward test #${forwardTestId}` });
  const heading = chartPanel.getByRole('heading', { level: 1 });
  await expect(heading).toContainText(`#${forwardTestId}`);
  await expect(heading.getByRole('link', { name: `${strategyName} v1` })).toBeVisible();
  await expect(heading.getByRole('link', { name: symbol, exact: true })).toBeVisible();
  await expect(heading).toContainText('1 min');
  // The worker compares the states every 2 seconds, and the page reads the forward test every 2 seconds.
  const status = chartPanel.getByRole('status', { name: 'Forward test status' });
  await expect(status).toHaveText('Running', { timeout: STATUS_TIMEOUT_MILLISECONDS });
  // The list shows the status from /ws/forward-tests. The open forward test is the current row.
  const list = page.getByRole('complementary', { name: 'Forward tests' });
  await expect(list.getByRole('link', { name: `#${forwardTestId}`, exact: true })).toHaveAttribute('aria-current', 'page');
  const row = list.getByRole('row', { name: new RegExp(symbol) });
  await expect(row).toContainText('Running', { timeout: STATUS_TIMEOUT_MILLISECONDS });
  // The Logs tab lists the start, and the planned stop at the end time.
  const tables = page.getByRole('region', { name: 'Forward test tables' });
  await tables.getByRole('tab', { name: 'Logs' }).click();
  await expect(tables.getByRole('row', { name: /Started/ })).toContainText('2026-01-02 03:04:05 UTC');
  await expect(tables.getByRole('row', { name: /Planned stop/ })).toBeVisible();
  await expectNoPageScroll(page);

  // The order panel of the instrument page does not send a paper order by hand on the instrument of the running
  // forward test, and says why.
  await page.goto(`/instruments/ARCA/${symbol}?currency=USD`);
  const ticket = page.getByRole('form', { name: `Paper order of ${symbol}`, exact: true });
  const reviewButton = ticket.getByRole('button', { name: 'Review buy order' });
  // The page reads the running forward tests from /ws/forward-tests after it opens.
  await expect(reviewButton).toHaveAccessibleDescription(
    `Forward test ${forwardTestId} (${strategyName} v1) trades ${symbol} / ARCA. Stop the forward test to send an order by hand.`,
    { timeout: STATUS_TIMEOUT_MILLISECONDS },
  );
  await expect(reviewButton).toBeDisabled();

  await page.goBack();
  const stopButton = chartPanel.getByRole('button', { name: 'Stop forward test', exact: true });
  // The Stop icon is red: the support error color of the Carbon theme.
  const iconColors = await stopButton.locator('path').first().evaluate((path) => {
    const probe = document.createElement('span');
    probe.style.color = 'var(--cds-support-error)';
    document.body.append(probe);
    const errorColor = getComputedStyle(probe).color;
    probe.remove();
    return { fill: getComputedStyle(path).fill, errorColor };
  });
  expect(iconColors.fill).toBe(iconColors.errorColor);
  await stopButton.click();

  await expect(status).toHaveText('Stopped', { timeout: STATUS_TIMEOUT_MILLISECONDS });
  await expect(row).toContainText('Stopped', { timeout: STATUS_TIMEOUT_MILLISECONDS });
  // A stopped forward test has no Stop button.
  await expect(stopButton).toHaveCount(0);
});

test('the forward test list has a visible scroll track', async ({ page }) => {
  await page.goto('/forward-tests');

  const list = page.getByRole('region', { name: 'Forward test list' });
  const track = page.getByRole('scrollbar', { name: 'Forward test list scroll bar' });
  const lastRow = list.getByRole('row').last();
  await expect(track).toBeVisible({ timeout: STATUS_TIMEOUT_MILLISECONDS });
  await expect(track.locator('.scroll-thumb')).toBeVisible();
  await expect(lastRow).not.toBeInViewport();

  await track.focus();
  await page.keyboard.press('End');

  await expect(lastRow).toBeInViewport();
  await expect(track).toHaveAttribute('aria-valuenow', '100');
  await expectNoPageScroll(page);
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

  const forwardTests = page.getByRole('region', { name: 'Forward test list' });
  const columnHeaders = forwardTests.getByRole('columnheader');
  // The list comes from the e2e server, which the backtest children of other tests slow.
  await expect(columnHeaders.first()).toBeVisible({ timeout: STATUS_TIMEOUT_MILLISECONDS });
  for (const columnHeader of await columnHeaders.all()) {
    expect(await findBrokenWords(columnHeader)).toEqual([]);
  }
  // The table is not wider than its region, so no column is out of reach.
  expect(await forwardTests.evaluate((region) => region.scrollWidth <= region.clientWidth)).toBe(true);
});
