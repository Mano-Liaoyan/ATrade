// Each side column has a vertical splitter on its inner edge (#177, spec section 25.13): a drag, the arrow keys, Home,
// End, and a double-click change the width. The browser keeps the width and the minimized state after a reload.
// Against the real backend with the IBKR fake (backend/tests/e2e_server.py).
import { expect, test, type Locator, type Page } from '@playwright/test';

const PAGE_PATH = '/instruments/SEHK/700?currency=HKD&bar_period=1-HOUR';

async function openWorkbench(page: Page): Promise<void> {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto(PAGE_PATH);
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('2160 bars');
}

async function readNumber(locator: Locator, attribute: string): Promise<number> {
  return Number(await locator.getAttribute(attribute));
}

async function readWidth(locator: Locator): Promise<number> {
  return Math.round((await locator.boundingBox())?.width ?? 0);
}

test('the splitter of the watchlist changes its width with a drag, the keys, and a double-click', async ({ page }) => {
  await openWorkbench(page);
  const column = page.getByRole('complementary', { name: 'Watchlist' });
  const splitter = page.getByRole('separator', { name: 'Resize watchlist' });
  await expect(splitter).toHaveAttribute('aria-orientation', 'vertical');
  // The default width 20rem.
  await expect(splitter).toHaveAttribute('aria-valuenow', '320');
  expect(await readNumber(splitter, 'aria-valuemin')).toBe(256);
  const max = await readNumber(splitter, 'aria-valuemax');
  // 60% of the workbench, and 24rem for the center area beside the 20rem paper order column.
  expect(max).toBeGreaterThan(320);
  expect(max).toBeLessThanOrEqual(1280 - 320 - 384);

  const box = await splitter.boundingBox();
  if (box === null) {
    throw new Error('The splitter has no box.');
  }
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width / 2 + 100, box.y + box.height / 2, { steps: 4 });
  await page.mouse.up();
  await expect(splitter).toHaveAttribute('aria-valuenow', '420');
  await expect.poll(() => readWidth(column)).toBe(420);

  await splitter.focus();
  await page.keyboard.press('ArrowRight');
  await expect(splitter).toHaveAttribute('aria-valuenow', '436');
  await page.keyboard.press('ArrowLeft');
  await page.keyboard.press('ArrowLeft');
  await expect(splitter).toHaveAttribute('aria-valuenow', '404');
  await page.keyboard.press('End');
  await expect(splitter).toHaveAttribute('aria-valuenow', String(max));
  await page.keyboard.press('Home');
  await expect(splitter).toHaveAttribute('aria-valuenow', '256');
  await expect.poll(() => readWidth(column)).toBe(256);

  await splitter.dblclick();
  await expect(splitter).toHaveAttribute('aria-valuenow', '320');
});

test('the paper order column gets wider when its splitter moves left', async ({ page }) => {
  await openWorkbench(page);
  const splitter = page.getByRole('separator', { name: 'Resize paper order' });

  await splitter.focus();
  await page.keyboard.press('ArrowLeft');

  await expect(splitter).toHaveAttribute('aria-valuenow', '336');
});

test('a minimized column opens with the width from before, also after a reload', async ({ page }) => {
  await openWorkbench(page);
  const column = page.getByRole('complementary', { name: 'Watchlist' });
  const splitter = page.getByRole('separator', { name: 'Resize watchlist' });
  await splitter.focus();
  await page.keyboard.press('ArrowRight');
  await page.keyboard.press('ArrowRight');
  await expect(splitter).toHaveAttribute('aria-valuenow', '352');

  await page.getByRole('button', { name: 'Minimize watchlist' }).click();
  await expect(splitter).toBeHidden();
  await expect.poll(() => readWidth(column)).toBe(32);

  await page.reload();
  await expect(page.getByRole('button', { name: 'Open watchlist' })).toBeVisible();
  await page.getByRole('button', { name: 'Open watchlist' }).click();

  await expect(page.getByRole('separator', { name: 'Resize watchlist' })).toHaveAttribute('aria-valuenow', '352');
  await expect.poll(() => readWidth(column)).toBe(352);
  await page.reload();
  await expect(page.getByRole('separator', { name: 'Resize watchlist' })).toHaveAttribute('aria-valuenow', '352');
});

test('the paper order form keeps its values while the column is minimized', async ({ page }) => {
  await openWorkbench(page);
  const quantity = page.getByRole('form', { name: 'Paper order' }).getByRole('textbox', { name: 'Quantity' });
  await quantity.fill('7');

  await page.getByRole('button', { name: 'Minimize paper order' }).click();
  await page.getByRole('button', { name: 'Open paper order' }).click();

  await expect(quantity).toHaveValue('7');
});
