// HK instrument list editor on the settings page, against the real backend with the IBKR fake. The Playwright projects
// share one database and run at the same time, so each project uses its own symbols <PROJECT NAME>HK01 ...
// <PROJECT NAME>HK20 (backend/tests/e2e_server.py).
import { expect, test, type APIRequestContext, type Locator, type Page, type TestInfo } from '@playwright/test';

const HK_INSTRUMENT_LIST_PATH = '/api/market-data/hk-instrument-list';
const INSTRUMENTS_PER_PROJECT = 20;

interface HkInstrument {
  id: number;
  symbol: string;
}

function symbolStart(currentTest: TestInfo): string {
  return `${currentTest.project.name.toUpperCase()}HK`;
}

function projectSymbol(currentTest: TestInfo, number: number): string {
  return `${symbolStart(currentTest)}${String(number).padStart(2, '0')}`;
}

// Deletes the instruments of this project, so each test starts with none of them in the list.
async function clearProjectInstruments(request: APIRequestContext, currentTest: TestInfo): Promise<void> {
  const listResponse = await request.get(HK_INSTRUMENT_LIST_PATH);
  const hkInstrumentList = (await listResponse.json()) as { instruments: HkInstrument[] };
  for (const instrument of hkInstrumentList.instruments) {
    if (instrument.symbol.startsWith(symbolStart(currentTest))) {
      await request.delete(`${HK_INSTRUMENT_LIST_PATH}/${String(instrument.id)}`);
    }
  }
}

async function pasteSymbols(page: Page, text: string): Promise<void> {
  await page.getByLabel('Symbols', { exact: true }).fill(text);
  await page.getByRole('button', { name: 'Add to HK instrument list' }).click();
}

test.beforeEach(async ({ request }, currentTest) => {
  await clearProjectInstruments(request, currentTest);
});

test('adds pasted symbols, shows the result of each symbol, and deletes a row', async ({ page }, currentTest) => {
  const first = projectSymbol(currentTest, 1);
  const second = projectSymbol(currentTest, 2);
  const unknown = `${symbolStart(currentTest)}XX`;
  await page.goto('/');
  await page.getByRole('link', { name: 'Settings', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'HK instrument list' })).toBeVisible();

  await pasteSymbols(page, `${first}, ${second}\n${unknown}`);

  const results = page.getByRole('list', { name: 'Add results' });
  // Each result is the symbol with a status icon before it. The icon has the result as its name and tooltip.
  const resultStatus = (symbol: string, status: string): Locator =>
    results.getByRole('listitem').filter({ hasText: symbol }).getByRole('img', { name: status, exact: true });
  await expect(resultStatus(first, 'Added')).toBeVisible();
  await expect(resultStatus(second, 'Added')).toBeVisible();
  await expect(resultStatus(unknown, 'Not found')).toBeVisible();
  const table = page.getByRole('region', { name: 'HK instrument list table' });
  await expect(table.getByRole('rowheader', { name: first, exact: true })).toBeVisible();
  await expect(table.getByRole('rowheader', { name: second, exact: true })).toBeVisible();
  await expect(table.getByRole('rowheader', { name: unknown, exact: true })).toHaveCount(0);

  await pasteSymbols(page, first);
  await expect(resultStatus(first, 'Already in list')).toBeVisible();

  await table.getByRole('button', { name: `Delete ${first} from the HK instrument list` }).click();
  await expect(table.getByRole('rowheader', { name: first, exact: true })).toHaveCount(0);
  await page.reload();
  await expect(table.getByRole('rowheader', { name: second, exact: true })).toBeVisible();
  await expect(table.getByRole('rowheader', { name: first, exact: true })).toHaveCount(0);
});

test('a long HK instrument list scrolls in its own visible scroll track', async ({ page, request }, currentTest) => {
  const symbols = Array.from({ length: INSTRUMENTS_PER_PROJECT }, (_, index) => projectSymbol(currentTest, index + 1));
  // eslint-disable-next-line @typescript-eslint/naming-convention -- `data` is the request body option of Playwright.
  await request.post(HK_INSTRUMENT_LIST_PATH, { data: { symbols } });
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.goto('/settings');

  const table = page.getByRole('region', { name: 'HK instrument list table' });
  await expect(table.getByRole('rowheader', { name: symbols.at(-1), exact: true })).toBeAttached();
  // Other projects can have instruments after ours. The page reads the list once, so its last row stays the same.
  const lastInstrument = table.getByRole('row').last();
  await expect(lastInstrument).not.toBeInViewport();
  const scrollTrack = page.getByRole('scrollbar', { name: 'HK instrument list table scroll bar' });
  await expect(scrollTrack).toBeVisible();

  await scrollTrack.focus();
  await page.keyboard.press('End');

  await expect(lastInstrument).toBeInViewport();
  await expect(scrollTrack).toHaveAttribute('aria-valuenow', '100');
});
