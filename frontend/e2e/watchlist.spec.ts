// Watchlist against the real backend with the IBKR fake. The Playwright projects share one database and run at the same
// time, so each project uses its own instruments <PROJECT NAME>01 ... <PROJECT NAME>25 (backend/tests/e2e_server.py).
import { expect, test, type APIRequestContext, type Locator, type Page, type TestInfo, type WebSocketRoute } from '@playwright/test';

const WATCHLIST_PATH = '/api/watchlist';
const INSTRUMENTS_PER_PROJECT = 25;

interface WatchlistInstrument {
  id: number;
  symbol: string;
}

function projectSymbol(currentTest: TestInfo, number: number): string {
  return `${currentTest.project.name.toUpperCase()}${String(number).padStart(2, '0')}`;
}

// Deletes the instruments of this project, so each test starts with none of them in the watchlist.
async function clearProjectInstruments(request: APIRequestContext, currentTest: TestInfo): Promise<void> {
  const symbolStart = currentTest.project.name.toUpperCase();
  const listResponse = await request.get(WATCHLIST_PATH);
  const watchlist = (await listResponse.json()) as { instruments: WatchlistInstrument[] };
  for (const instrument of watchlist.instruments) {
    if (instrument.symbol.startsWith(symbolStart)) {
      await request.delete(`${WATCHLIST_PATH}/${String(instrument.id)}`);
    }
  }
}

async function addThroughBackend(request: APIRequestContext, symbol: string): Promise<void> {
  const instrument = { symbol, exchange: 'ARCA', currency: 'USD' };
  // eslint-disable-next-line @typescript-eslint/naming-convention -- `data` is the request body option of Playwright.
  await request.post(WATCHLIST_PATH, { data: instrument });
}

// The search runs while the user types. There is no Search button.
async function searchFor(page: Page, query: string): Promise<void> {
  await page.getByLabel('Symbol', { exact: true }).fill(query);
}

test.beforeEach(async ({ request }, currentTest) => {
  await clearProjectInstruments(request, currentTest);
});

function watchlistColumn(page: Page): Locator {
  return page.getByRole('complementary', { name: 'Watchlist' });
}

test('adds an instrument from the search, keeps it after a reload, and deletes it', async ({ page }, currentTest) => {
  const symbol = projectSymbol(currentTest, 1);
  const instrumentName = `${symbol} / ARCA / USD`;
  await page.goto('/');

  await searchFor(page, symbol);
  await page.getByRole('option', { name: instrumentName }).click();

  const watchlistTable = watchlistColumn(page).getByRole('region', { name: 'Watchlist table' });
  await expect(watchlistTable.getByRole('link', { name: symbol, exact: true })).toBeVisible();
  // The candidate list marks an instrument that is in the watchlist.
  await page.getByLabel('Symbol', { exact: true }).press('ArrowDown');
  const savedOption = page.getByRole('option', { name: instrumentName });
  await expect(savedOption).toContainText('In watchlist');
  await expect(savedOption).toHaveAttribute('aria-disabled', 'true');
  await page.getByLabel('Symbol', { exact: true }).press('Escape');

  await page.reload();
  await expect(watchlistTable.getByRole('link', { name: symbol, exact: true })).toBeVisible();

  await watchlistColumn(page).getByRole('button', { name: `Delete ${instrumentName} from the watchlist` }).click();
  await expect(watchlistColumn(page).getByRole('link', { name: symbol, exact: true })).toHaveCount(0);
  await page.reload();
  await expect(watchlistColumn(page).getByRole('heading', { name: 'Watchlist' })).toBeVisible();
  await expect(watchlistColumn(page).getByRole('link', { name: symbol, exact: true })).toHaveCount(0);
});

test('shows one row when the live push reads the list before the add response arrives', async ({ page }, currentTest) => {
  const symbol = projectSymbol(currentTest, 3);
  // A fake /ws/watchlist socket sends the change push of the add. The list read after the push comes back before the
  // response of the add.
  const watchlistSocket = new Promise<WebSocketRoute>((resolve) => {
    void page.routeWebSocket(/\/ws\/watchlist$/, resolve);
  });
  await page.route(`**${WATCHLIST_PATH}`, async (route) => {
    if (route.request().method() !== 'POST') {
      await route.fallback();
      return;
    }
    const addResponse = await route.fetch();
    const listReadWithInstrument = page.waitForResponse(
      async (response) =>
        response.request().method() === 'GET' &&
        response.url().endsWith(WATCHLIST_PATH) &&
        (await response.text()).includes(`"${symbol}"`),
    );
    (await watchlistSocket).send(JSON.stringify({ type: 'changed' }));
    await listReadWithInstrument;
    await route.fulfill({ response: addResponse });
  });
  await page.goto('/');

  await searchFor(page, symbol);
  const addResponse = page.waitForResponse((response) => response.request().method() === 'POST');
  await page.getByRole('option', { name: `${symbol} / ARCA / USD` }).click();
  await addResponse;

  const watchlistTable = watchlistColumn(page).getByRole('region', { name: 'Watchlist table' });
  await expect(watchlistTable.getByRole('link', { name: symbol, exact: true })).toHaveCount(1);
});

test('a watchlist instrument opens its instrument page',async ({ page, request }, currentTest) => {
  const symbol = projectSymbol(currentTest, 2);
  await addThroughBackend(request, symbol);
  await page.goto('/');

  await watchlistColumn(page).getByRole('link', { name: symbol, exact: true }).click();

  await expect(page).toHaveURL(`/instruments/ARCA/${symbol}?currency=USD`);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(`${symbol} / ARCA / USD`);
});

test('long watchlist has a visible scroll track and the last instrument is reachable', async ({ page, request }, currentTest) => {
  for (let number = 1; number <= INSTRUMENTS_PER_PROJECT; number += 1) {
    await addThroughBackend(request, projectSymbol(currentTest, number));
  }
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.goto('/');

  const watchlistTable = watchlistColumn(page).getByRole('region', { name: 'Watchlist table' });
  await expect(watchlistTable.getByRole('link', { name: projectSymbol(currentTest, INSTRUMENTS_PER_PROJECT), exact: true })).toBeAttached();
  // Other projects can have instruments after ours. The page reads the list once, so its last row stays the same.
  const lastInstrument = watchlistTable.getByRole('row').last();
  await expect(lastInstrument).not.toBeInViewport();
  const scrollTrack = page.getByRole('scrollbar', { name: 'Watchlist table scroll bar' });
  await expect(scrollTrack).toBeVisible();

  await scrollTrack.focus();
  await page.keyboard.press('End');

  await expect(lastInstrument).toBeInViewport();
  await expect(scrollTrack).toHaveAttribute('aria-valuenow', '100');
});

test('each row shows the live last price and its change from the previous close', async ({ page, request }, currentTest) => {
  const symbol = projectSymbol(currentTest, 4);
  await addThroughBackend(request, symbol);
  await page.goto('/');

  // The last complete daily bar of the fake is 2026-01-01 (close 104.50). The fake updates the daily bar of
  // 2026-01-02 over /ws/watchlist-live-bars: the close moves from 105 to 106.75. Without it the row shows 104.50.
  const row = watchlistColumn(page)
    .getByRole('row')
    .filter({ has: page.getByRole('link', { name: symbol, exact: true }) });
  const lastCell = row.getByRole('cell').first();
  await expect(lastCell).toHaveText(/^10[56]\.\d\d$/);
  const firstLast = (await lastCell.textContent())?.trim() ?? '';
  await expect(lastCell).not.toHaveText(firstLast);

  // One read of both cells: the live bar changes a few times each second.
  const cells = await row.evaluate((rowElement) => Array.from(rowElement.querySelectorAll('td'), (cell) => cell.textContent.trim()));
  const previousClose = 104.5;
  const changePercent = ((Number(cells[0]) - previousClose) / previousClose) * 100;
  expect(cells[1]).toBe(`+${changePercent.toFixed(2)} %`);
});

test('a row and the instrument page show one quote before the click, on the open page, and after the user leaves', async ({
  page,
  request,
}, currentTest) => {
  const symbol = projectSymbol(currentTest, 5);
  const otherSymbol = projectSymbol(currentTest, 6);
  await addThroughBackend(request, symbol);
  await addThroughBackend(request, otherSymbol);
  // Fake live sockets. The first /ws/watchlist-live-bars socket sends one live daily bar of 2026-01-02 (close 107);
  // the sockets after a page change send nothing, so no new tick arrives. The page live bars come only when the test
  // sends them. The last complete daily bar is 2026-01-01 (close 104.50; the day before closed at 103.50).
  const liveDailyBar = { time: 1_767_312_000, open: 105, high: 108, low: 104, close: 107, volume: 10 };
  let watchlistSockets = 0;
  await page.routeWebSocket(/\/ws\/watchlist-live-bars$/, (socket) => {
    watchlistSockets += 1;
    if (watchlistSockets === 1) {
      socket.send(JSON.stringify({ type: 'live_bars', live_bars: [{ symbol, exchange: 'ARCA', currency: 'USD', bar: liveDailyBar }] }));
    }
  });
  let chartSocket: WebSocketRoute | undefined;
  await page.routeWebSocket(/\/ws\/market-data\?/, (socket) => {
    chartSocket = socket;
  });
  let openBarReads = 0;
  page.on('request', (sent) => {
    if (sent.url().includes('/api/market-data/bars?')) {
      openBarReads += 1;
    }
  });
  page.on('requestfinished', (finished) => {
    if (finished.url().includes('/api/market-data/bars?')) {
      openBarReads -= 1;
    }
  });
  page.on('requestfailed', (failed) => {
    if (failed.url().includes('/api/market-data/bars?')) {
      openBarReads -= 1;
    }
  });
  const readRow = (rowSymbol: string): Promise<string[]> =>
    watchlistColumn(page)
      .getByRole('row')
      .filter({ has: page.getByRole('link', { name: rowSymbol, exact: true }) })
      .evaluate((rowElement) => Array.from(rowElement.querySelectorAll('td'), (cell) => cell.textContent.trim()).slice(0, 2));
  const lastPrice = page.getByLabel('Last price', { exact: true });
  const change = page.getByLabel('Change from the previous close', { exact: true });
  await page.goto('/');

  // Before the click.
  await expect.poll(() => readRow(symbol)).toEqual(['107.00', '+2.39 %']);

  // On the open page, before its own live bar: all bar reads (the daily bars of the page too) are done.
  await watchlistColumn(page).getByRole('link', { name: symbol, exact: true }).click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(`${symbol} / ARCA / USD`);
  await expect(page.getByRole('status', { name: 'Bar count' })).toBeAttached();
  await expect.poll(() => openBarReads).toBe(0);
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(resolve)));
  expect(await readRow(symbol)).toEqual(['107.00', '+2.39 %']);
  await expect(lastPrice).toHaveText('107.00');
  await expect(change).toHaveText('+2.50 (+2.39 %)');

  // The live bar of the page changes the header and the row together.
  expect(chartSocket).toBeDefined();
  chartSocket?.send(JSON.stringify({ type: 'bar', bar: { ...liveDailyBar, close: 108 } }));
  await expect(lastPrice).toHaveText('108.00');
  await expect(change).toHaveText('+3.50 (+3.35 %)');
  expect(await readRow(symbol)).toEqual(['108.00', '+3.35 %']);

  // After the user leaves: another instrument page, then the home page. The row keeps the last quote.
  await watchlistColumn(page).getByRole('link', { name: otherSymbol, exact: true }).click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(`${otherSymbol} / ARCA / USD`);
  expect(await readRow(symbol)).toEqual(['108.00', '+3.35 %']);
  await page.getByRole('link', { name: 'ATrade', exact: true }).click();
  await expect(page).toHaveURL('/');
  await expect.poll(() => openBarReads).toBe(0);
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(resolve)));
  expect(await readRow(symbol)).toEqual(['108.00', '+3.35 %']);
});
