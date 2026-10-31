// The tab line of a workbench panel never cuts a tab: in a narrow panel the tabs scroll sideways in their own strip
// with a visible track, and the panel buttons stay at the end of the line. The selected tab scrolls into view.
// backend/tests/e2e_server.py adds a failed HK backtest (700).
import { expect, test, type APIRequestContext } from '@playwright/test';

// The browser rounds the scroll width of the strip down to whole pixels, so a fully scrolled tab can miss a part of a
// pixel at its end.
const FULLY_VISIBLE_RATIO = 0.99;

async function findBacktestId(request: APIRequestContext, symbol: string): Promise<number> {
  const backtests = (await (await request.get('/api/backtests')).json()) as { id: number; symbol: string }[];
  const found = backtests.find((backtest) => backtest.symbol === symbol);
  expect(found).toBeDefined();
  return found?.id ?? 0;
}

test('the last backtest table tab in a narrow panel scrolls into view and the panel buttons stay visible', async ({ page, request }) => {
  await page.setViewportSize({ width: 1024, height: 768 });
  const backtestId = await findBacktestId(request, '700');
  await page.goto(`/backtests/${String(backtestId)}`);
  const tables = page.getByRole('region', { name: 'Backtest tables' });
  const firstTab = tables.getByRole('tab', { name: 'Trades', exact: true });
  const lastTab = tables.getByRole('tab', { name: 'Bar sources', exact: true });
  const minimize = tables.getByRole('button', { name: 'Minimize panel' });
  const maximize = tables.getByRole('button', { name: 'Maximize panel' });
  await expect(firstTab).toBeVisible();

  // The tabs overflow the narrow panel: the strip shows its own track, and the panel buttons are not covered.
  const track = tables.getByRole('scrollbar', { name: 'Backtest tables scroll bar' });
  await expect(track).toBeVisible();
  await expect(track.locator('.scroll-thumb')).toBeVisible();
  await expect(minimize).toBeInViewport({ ratio: 1 });
  await expect(maximize).toBeInViewport({ ratio: 1 });
  await expect(lastTab).not.toBeInViewport({ ratio: FULLY_VISIBLE_RATIO });

  // The End key selects the last tab and scrolls it into view, clear of the panel buttons.
  await firstTab.click();
  await page.keyboard.press('End');
  await expect(lastTab).toHaveAttribute('aria-selected', 'true');
  await expect(lastTab).toBeInViewport({ ratio: FULLY_VISIBLE_RATIO });
  const lastTabBox = await lastTab.boundingBox();
  const minimizeBox = await minimize.boundingBox();
  expect(lastTabBox).not.toBeNull();
  expect(minimizeBox).not.toBeNull();
  expect((lastTabBox?.x ?? 0) + (lastTabBox?.width ?? 0)).toBeLessThanOrEqual((minimizeBox?.x ?? 0) + 1);

  // The track scrolls the strip back; the arrow keys then move the selection and bring each tab into view.
  await track.focus();
  await page.keyboard.press('Home');
  await expect(firstTab).toBeInViewport({ ratio: FULLY_VISIBLE_RATIO });
  await expect(lastTab).not.toBeInViewport({ ratio: FULLY_VISIBLE_RATIO });
  await track.focus();
  await page.keyboard.press('End');
  await expect(lastTab).toBeInViewport({ ratio: FULLY_VISIBLE_RATIO });
  await tables.getByRole('tab', { name: 'Trades', exact: true }).click();
  await expect(firstTab).toBeInViewport({ ratio: FULLY_VISIBLE_RATIO });
  await page.keyboard.press('ArrowLeft');
  await expect(lastTab).toHaveAttribute('aria-selected', 'true');
  await expect(lastTab).toBeInViewport({ ratio: FULLY_VISIBLE_RATIO });

  // A click on the last tab shows its table.
  await firstTab.click();
  await track.focus();
  await page.keyboard.press('End');
  await lastTab.click();
  await expect(tables.getByRole('region', { name: 'Bar sources' })).toBeVisible();
});
