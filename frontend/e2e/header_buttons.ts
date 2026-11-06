// Each control of a run header line stays clickable at the small desktop widths: no other control lies over it.
import { expect, type Locator, type Page } from '@playwright/test';

const SMALL_DESKTOP_SIZES = [
  { width: 1280, height: 720 },
  { width: 1366, height: 768 },
];

export async function expectHeaderButtonsClickable(page: Page, panel: Locator): Promise<void> {
  const buttons = panel.locator('.atrade-panel-header').first().getByRole('button');
  for (const size of SMALL_DESKTOP_SIZES) {
    await page.setViewportSize(size);
    for (const button of await buttons.all()) {
      const isOnTop = await button.evaluate((element) => {
        const box = element.getBoundingClientRect();
        const target = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2);
        return target !== null && element.contains(target);
      });
      expect(isOnTop, (await button.getAttribute('aria-label')) ?? '').toBe(true);
    }
  }
}
