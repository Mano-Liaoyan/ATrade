// Instrument search against the real backend with the IBKR fake (backend/tests/fakes/ibkr.py has the instruments).
import { expect, test, type Page } from '@playwright/test';

async function searchFor(page: Page, query: string): Promise<void> {
  await page.goto('/');
  await page.getByLabel('Symbol', { exact: true }).fill(query);
  await page.getByRole('button', { name: 'Search' }).click();
}

test('finds an instrument and shows symbol, exchange, and currency', async ({ page }) => {
  await searchFor(page, '700');

  const results = page.getByRole('region', { name: 'Instrument search results' }).getByRole('listitem');
  await expect(results).toHaveCount(1);
  await expect(results).toContainText(['700 / SEHK / HKD']);
});

test('says that no instrument matches', async ({ page }) => {
  await searchFor(page, 'ZZZZ');

  await expect(page.getByText('No instrument matches "ZZZZ".')).toBeVisible();
});

test('long result list has a visible scroll track and every result is reachable', async ({ page }) => {
  await searchFor(page, 'A');

  const resultRegion = page.getByRole('region', { name: 'Instrument search results' });
  const lastResult = resultRegion.getByRole('listitem').last();
  await expect(lastResult).toContainText('AZO / NASDAQ / USD');
  await expect(lastResult).not.toBeInViewport();
  const scrollTrack = page.getByRole('scrollbar', { name: 'Instrument search results scroll bar' });
  await expect(scrollTrack).toBeVisible();

  await scrollTrack.focus();
  await page.keyboard.press('End');

  await expect(lastResult).toBeInViewport();
  await expect(scrollTrack).toHaveAttribute('aria-valuenow', '100');
});

test('scrolling the result list with the mouse wheel moves the app scroll thumb', async ({ page }) => {
  await searchFor(page, 'A');

  const resultRegion = page.getByRole('region', { name: 'Instrument search results' });
  const lastResult = resultRegion.getByRole('listitem').last();
  await expect(lastResult).toContainText('AZO / NASDAQ / USD');
  await resultRegion.hover();
  // Firefox scrolls at most about one page for each wheel event, so the test sends several.
  await expect(async () => {
    await page.mouse.wheel(0, 300);
    await expect(lastResult).toBeInViewport({ timeout: 500 });
  }).toPass();
  const scrollTrack = page.getByRole('scrollbar', { name: 'Instrument search results scroll bar' });
  await expect(scrollTrack).toHaveAttribute('aria-valuenow', '100');
});

test('dragging the app scroll thumb to the end of the track shows the last result', async ({ page }) => {
  await searchFor(page, 'A');

  const scrollTrack = page.getByRole('scrollbar', { name: 'Instrument search results scroll bar' });
  const trackBox = await scrollTrack.boundingBox();
  if (trackBox === null) {
    throw new Error('The scroll track has no box.');
  }
  await page.mouse.move(trackBox.x + trackBox.width / 2, trackBox.y + 5);
  await page.mouse.down();
  await page.mouse.move(trackBox.x + trackBox.width / 2, trackBox.y + trackBox.height + 50, { steps: 5 });
  await page.mouse.up();

  const lastResult = page.getByRole('region', { name: 'Instrument search results' }).getByRole('listitem').last();
  await expect(lastResult).toBeInViewport();
  await expect(scrollTrack).toHaveAttribute('aria-valuenow', '100');
});

test('shows the backend message when IB Gateway is not reachable', async ({ page }) => {
  // The e2e server has one fake Gateway that is reachable, so this test gives the 503 answer of the backend route.
  await page.route('**/api/market-data/instrument-search?*', (route) =>
    route.fulfill({
      status: 503,
      json: { detail: 'IB Gateway is not reachable at ib-gateway:4004. Instrument search needs IB Gateway.' },
    }),
  );

  await searchFor(page, '700');

  await expect(page.getByRole('alert')).toHaveText(
    'IB Gateway is not reachable at ib-gateway:4004. Instrument search needs IB Gateway.',
  );
});
