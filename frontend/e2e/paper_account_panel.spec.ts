// The account panel with the IBKR fake of backend/tests/e2e_server.py: account DU1234567, a balance, and 40 positions.
import { expect, test } from '@playwright/test';

test('account panel shows the checked paper account and its balance', async ({ page }) => {
  await page.goto('/');

  await expect(page.getByRole('status', { name: 'Paper account check' })).toHaveText('Paper account DU1234567 checked.');
  const balance = page.getByRole('definition');
  await expect(balance.first()).toHaveText('101,234.50');
  await expect(balance.nth(1)).toHaveText('25,000.00');
});

test('position table has a visible scroll track and its last row can be scrolled into view', async ({ page }) => {
  await page.goto('/');
  const positions = page.getByRole('region', { name: 'Positions' });
  const lastRow = positions.getByRole('row', { name: /TEST40/ });
  const track = page.getByRole('scrollbar', { name: 'Positions vertical scroll bar' });
  const thumb = track.locator('[data-scroll-thumb="vertical"]');

  await expect(positions.getByRole('row', { name: /TEST01/ })).toBeInViewport();
  await expect(track).toBeVisible();
  await expect(thumb).toBeVisible();
  await expect(lastRow).not.toBeInViewport();

  const thumbBox = await thumb.boundingBox();
  const trackBox = await track.boundingBox();
  if (thumbBox === null || trackBox === null) {
    throw new Error('The scroll track is not drawn.');
  }
  const thumbCenterX = thumbBox.x + thumbBox.width / 2;
  await page.mouse.move(thumbCenterX, thumbBox.y + thumbBox.height / 2);
  await page.mouse.down();
  await page.mouse.move(thumbCenterX, trackBox.y + trackBox.height + thumbBox.height, { steps: 5 });
  await page.mouse.up();

  await expect(lastRow).toBeInViewport();
  await expect(thumb).toBeVisible();
});
