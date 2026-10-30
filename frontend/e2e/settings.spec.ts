// Settings page against the real backend. The source order is one global value and the Playwright projects run at the
// same time against one database, so each project changes it only while it holds a lock directory.
import { expect, test, type APIRequestContext } from '@playwright/test';
import { mkdir, rm, stat } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';

const SOURCE_ORDER_PATH = '/api/market-data/source-order';
const LOCK_DIRECTORY = path.join(tmpdir(), `atrade-e2e-source-order-${process.env['ATRADE_E2E_PORT'] ?? '4173'}`);
const LOCK_RETRY_MILLISECONDS = 100;

type BarSource = 'ibkr' | 'databento';

// A lock older than this is left from a run that stopped. A test holds the lock for a few seconds only.
const STALE_LOCK_MILLISECONDS = 60_000;

async function holdSourceOrderLock(): Promise<void> {
  for (;;) {
    try {
      await mkdir(LOCK_DIRECTORY);
      return;
    } catch {
      const lockAge = await stat(LOCK_DIRECTORY).then(
        (lockStat) => Date.now() - lockStat.mtimeMs,
        () => 0,
      );
      if (lockAge > STALE_LOCK_MILLISECONDS) {
        await rm(LOCK_DIRECTORY, { recursive: true, force: true });
      }
      await new Promise((resolve) => setTimeout(resolve, LOCK_RETRY_MILLISECONDS));
    }
  }
}

async function putSourceOrder(request: APIRequestContext, sourceOrder: BarSource[]): Promise<void> {
  // eslint-disable-next-line @typescript-eslint/naming-convention -- `data` is the request body option of Playwright.
  await request.put(SOURCE_ORDER_PATH, { data: { source_order: sourceOrder } });
}

test.beforeEach(async ({ request }) => {
  await holdSourceOrderLock();
  await putSourceOrder(request, ['ibkr', 'databento']);
});

test.afterEach(async ({ request }) => {
  await putSourceOrder(request, ['ibkr', 'databento']);
  await rm(LOCK_DIRECTORY, { recursive: true, force: true });
});

test('moves a bar source and shows the new source order after the page opens again', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('navigation', { name: 'Pages' }).getByRole('link', { name: 'Settings' }).click();
  await expect(page).toHaveURL('/settings');

  const sourceOrder = page.getByRole('table', { name: 'Source order' });
  // A row text starts with the bar source name. The tooltip of a hovered move button follows it.
  await expect(sourceOrder.getByRole('row')).toHaveText([/^\s*IBKR/, /^\s*Databento/]);
  // The first row has no up button and the last row has no down button.
  await expect(sourceOrder.getByRole('button', { name: 'Move IBKR up' })).toHaveCount(0);
  await expect(sourceOrder.getByRole('button', { name: 'Move Databento down' })).toHaveCount(0);

  const savedOrder = page.waitForRequest((sentRequest) => sentRequest.method() === 'PUT');
  await sourceOrder.getByRole('button', { name: 'Move IBKR down' }).click();
  expect((await savedOrder).postDataJSON()).toEqual({ source_order: ['databento', 'ibkr'] });
  await expect(sourceOrder.getByRole('row')).toHaveText([/^\s*Databento/, /^\s*IBKR/]);

  await page.reload();

  await expect(sourceOrder.getByRole('row')).toHaveText([/^\s*Databento/, /^\s*IBKR/]);
  await expect(sourceOrder.getByRole('button', { name: 'Move Databento up' })).toHaveCount(0);
});

test('shows the detail text of the backend when the save fails', async ({ page }) => {
  await page.route(SOURCE_ORDER_PATH, async (route) => {
    if (route.request().method() !== 'PUT') {
      await route.fallback();
      return;
    }
    await route.fulfill({ status: 422, json: { detail: 'The source order has a bar source 2 times.' } });
  });
  await page.goto('/settings');
  const sourceOrder = page.getByRole('table', { name: 'Source order' });

  await sourceOrder.getByRole('button', { name: 'Move IBKR down' }).click();

  await expect(page.getByRole('alert')).toHaveText('The source order has a bar source 2 times.');
  await expect(sourceOrder.getByRole('row')).toHaveText([/^\s*IBKR/, /^\s*Databento/]);
});
