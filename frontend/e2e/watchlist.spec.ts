// Watchlist against the real backend with the IBKR fake. The Playwright projects share one database and run at the same
// time, so each project uses its own instruments <PROJECT NAME>01 ... <PROJECT NAME>25 (backend/tests/e2e_server.py).
import { expect, test, type APIRequestContext, type Page, type TestInfo } from '@playwright/test';

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

async function searchFor(page: Page, query: string): Promise<void> {
  await page.getByLabel('Symbol', { exact: true }).fill(query);
  await page.getByRole('button', { name: 'Search' }).click();
}

test.beforeEach(async ({ request }, currentTest) => {
  await clearProjectInstruments(request, currentTest);
});

test('adds an instrument from the search, keeps it after a reload, and deletes it', async ({ page }, currentTest) => {
  const symbol = projectSymbol(currentTest, 1);
  const instrumentName = `${symbol} / ARCA / USD`;
  await page.goto('/');

  await searchFor(page, symbol);
  await page.getByRole('button', { name: `Add ${instrumentName} to the watchlist` }).click();

  const watchlistRegion = page.getByRole('region', { name: 'Watchlist instruments' });
  await expect(watchlistRegion.getByRole('link', { name: instrumentName })).toBeVisible();
  await expect(page.getByText('In watchlist')).toBeVisible();

  await page.reload();
  await expect(watchlistRegion.getByRole('link', { name: instrumentName })).toBeVisible();

  await page.getByRole('button', { name: `Delete ${instrumentName} from the watchlist` }).click();
  await expect(page.getByRole('link', { name: instrumentName })).toHaveCount(0);
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Watchlist' })).toBeVisible();
  await expect(page.getByRole('link', { name: instrumentName })).toHaveCount(0);
});

test('a watchlist instrument opens its instrument page', async ({ page, request }, currentTest) => {
  const symbol = projectSymbol(currentTest, 2);
  await addThroughBackend(request, symbol);
  await page.goto('/');

  await page.getByRole('link', { name: `${symbol} / ARCA / USD` }).click();

  await expect(page).toHaveURL(`/instruments/ARCA/${symbol}?currency=USD`);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(`${symbol} / ARCA / USD`);
});

test('long watchlist has a visible scroll track and the last instrument is reachable', async ({ page, request }, currentTest) => {
  for (let number = 1; number <= INSTRUMENTS_PER_PROJECT; number += 1) {
    await addThroughBackend(request, projectSymbol(currentTest, number));
  }
  await page.goto('/');

  const watchlistRegion = page.getByRole('region', { name: 'Watchlist instruments' });
  await expect(
    watchlistRegion.getByRole('link', { name: `${projectSymbol(currentTest, INSTRUMENTS_PER_PROJECT)} / ARCA / USD` }),
  ).toBeAttached();
  // Other projects can have instruments after ours. The page reads the list once, so its last item stays the same.
  const lastInstrument = watchlistRegion.getByRole('listitem').last();
  await expect(lastInstrument).not.toBeInViewport();
  const scrollTrack = page.getByRole('scrollbar', { name: 'Watchlist instruments scroll bar' });
  await expect(scrollTrack).toBeVisible();

  await scrollTrack.focus();
  await page.keyboard.press('End');

  await expect(lastInstrument).toBeInViewport();
  await expect(scrollTrack).toHaveAttribute('aria-valuenow', '100');
});
