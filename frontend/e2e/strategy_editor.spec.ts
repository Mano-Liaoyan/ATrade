// Strategy editor: create a strategy, edit and save its code, see a failed save, and keep unsaved edits after a reload.
import { expect, test, type Page, type TestInfo } from '@playwright/test';

const VALID_CODE = `from nautilus_trader.config import StrategyConfig
from nautilus_trader.trading import Strategy


class EmptyConfig(StrategyConfig):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)


class EmptyStrategy(Strategy):
    pass
`;

// The e2e database is not cleared between tests and browser projects, so each strategy name is unique.
function createUniqueName(currentTest: TestInfo, title: string): string {
  return `${title} ${currentTest.project.name} ${String(Date.now())}`;
}

async function createStrategy(page: Page, name: string): Promise<void> {
  await page.goto('/strategies');
  await page.getByLabel('Strategy name').fill(name);
  await page.getByRole('button', { name: 'Create strategy' }).click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(name);
}

async function replaceCode(page: Page, code: string): Promise<void> {
  const editor = page.getByRole('textbox', { name: 'Strategy code' });
  await editor.click();
  await page.keyboard.press('ControlOrMeta+a');
  await page.keyboard.insertText(code);
}

// The color of one screen pixel. The screenshot is decoded in the page, so the test needs no image library.
async function readPixel(page: Page, x: number, y: number): Promise<string> {
  const png = await page.screenshot({ clip: { x: Math.round(x), y: Math.round(y), width: 1, height: 1 } });
  return page.evaluate(async (base64) => {
    const image = await createImageBitmap(await (await fetch(`data:image/png;base64,${base64}`)).blob());
    const context = new OffscreenCanvas(1, 1).getContext('2d');
    context?.drawImage(image, 0, 0);
    return (context?.getImageData(0, 0, 1, 1).data ?? []).join(',');
  }, png.toString('base64'));
}

// A drag selects text on the line of the cursor. The line highlight of the cursor line must not hide the selection.
for (const colorScheme of ['light', 'dark'] as const) {
  test(`shows a mouse selection on the cursor line in the ${colorScheme} theme`, async ({ page }, currentTest) => {
    await page.emulateMedia({ colorScheme });
    await createStrategy(page, createUniqueName(currentTest, 'Select'));
    const line = page
      .getByRole('textbox', { name: 'Strategy code' })
      .locator('.cm-line', { hasText: 'class MovingAverageStrategy(Strategy):' });
    await line.scrollIntoViewIfNeeded();
    const box = await line.boundingBox();
    if (box === null) {
      throw new Error('The class line is not visible.');
    }
    const centerY = box.y + box.height / 2;

    await page.mouse.move(box.x + 2, centerY);
    await page.mouse.down();
    await page.mouse.move(box.x + 120, centerY, { steps: 5 });
    await page.mouse.up();

    // Above the letters, the selected part of the line and the part after the text have different colors.
    const topY = box.y + 1;
    expect(await readPixel(page, box.x + 60, topY)).not.toBe(await readPixel(page, box.x + box.width - 4, topY));
  });
}

// Tab indents in the editor. Escape and then Tab or Shift+Tab moves the focus out of the editor, so keyboard users
// can leave it. The editor is the last control of the page, so the test leaves it backwards.
test('Tab indents the code, and Escape then Shift+Tab leaves the editor', async ({ page }, currentTest) => {
  await createStrategy(page, createUniqueName(currentTest, 'Tab'));
  const editor = page.getByRole('textbox', { name: 'Strategy code' });
  await replaceCode(page, 'x = 1');
  await page.keyboard.press('Home');

  await page.keyboard.press('Tab');

  await expect(editor).toBeFocused();
  await expect(editor).toHaveText('    x = 1');

  await page.keyboard.press('Escape');
  await page.keyboard.press('Shift+Tab');
  await expect(editor).not.toBeFocused();
  await expect(editor).toHaveText('    x = 1');
});

test('creates a strategy that starts from the template as version 1', async ({ page }, currentTest) => {
  const name = createUniqueName(currentTest, 'Create');

  await createStrategy(page, name);

  await expect(page.getByRole('combobox', { name: 'Version' })).toHaveText(`${name} v1`);
  await expect(page.getByRole('textbox', { name: 'Strategy code' })).toContainText('class MovingAverageStrategy(Strategy):');
  await page.goto('/strategies');
  await expect(page.getByRole('link', { name: `${name} v1` })).toBeVisible();
});

test('saves edited code as a new version', async ({ page }, currentTest) => {
  const name = createUniqueName(currentTest, 'Save');
  await createStrategy(page, name);

  await replaceCode(page, VALID_CODE);
  await expect(page.getByText('Unsaved changes')).toBeVisible();
  await page.getByRole('button', { name: 'Save version' }).click();

  await expect(page.getByRole('status').filter({ hasText: 'Saved' })).toHaveText(`Saved as ${name} v2.`);
  await expect(page.getByRole('combobox', { name: 'Version' })).toHaveText(`${name} v2`);
  await expect(page.getByText('Unsaved changes')).toBeHidden();
  await expect(page.getByRole('textbox', { name: 'Strategy code' })).toContainText('class EmptyStrategy(Strategy):');
});

test('shows the line and the reason when the checks refuse the code', async ({ page }, currentTest) => {
  const name = createUniqueName(currentTest, 'Refuse');
  await createStrategy(page, name);

  await replaceCode(page, `${VALID_CODE}\nlimit = undefined_limit\n`);
  await page.getByRole('button', { name: 'Save version' }).click();

  await expect(page.getByRole('alert')).toContainText('Line 13: F821 Undefined name `undefined_limit`');
  await page.getByRole('combobox', { name: 'Version' }).click();
  await expect(page.getByRole('option')).toHaveText([`${name} v1`]);
  await page.keyboard.press('Escape');
  await expect(page.getByText('Unsaved changes')).toBeVisible();
});

test('keeps unsaved edits in the browser after a reload', async ({ page }, currentTest) => {
  const name = createUniqueName(currentTest, 'Draft');
  await createStrategy(page, name);

  await replaceCode(page, VALID_CODE);
  await expect(page.getByText('Unsaved changes')).toBeVisible();
  await page.reload();

  await expect(page.getByRole('textbox', { name: 'Strategy code' })).toContainText('class EmptyStrategy(Strategy):');
  await expect(page.getByText('Unsaved changes')).toBeVisible();
});

test('opens an older version from the version list', async ({ page }, currentTest) => {
  const name = createUniqueName(currentTest, 'Open');
  await createStrategy(page, name);
  await replaceCode(page, VALID_CODE);
  await page.getByRole('button', { name: 'Save version' }).click();
  await expect(page.getByRole('combobox', { name: 'Version' })).toHaveText(`${name} v2`);

  await page.getByRole('combobox', { name: 'Version' }).click();
  await page.getByRole('option', { name: `${name} v1` }).click();

  await expect(page.getByRole('combobox', { name: 'Version' })).toHaveText(`${name} v1`);
  await expect(page.getByRole('textbox', { name: 'Strategy code' })).toContainText('class MovingAverageStrategy(Strategy):');
});

test('deletes a strategy only after the confirmation', async ({ page }, currentTest) => {
  const name = createUniqueName(currentTest, 'Delete');
  await createStrategy(page, name);

  await page.getByRole('button', { name: 'Delete strategy' }).click();
  const dialog = page.getByRole('dialog', { name: `Delete ${name}` });
  await expect(dialog).toBeVisible();
  await dialog.getByRole('button', { name: 'Cancel' }).click();
  await expect(dialog).toBeHidden();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(name);

  await page.getByRole('button', { name: 'Delete strategy' }).click();
  await dialog.getByRole('button', { name: 'Delete strategy' }).click();

  await expect(page).toHaveURL(/\/strategies$/);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Strategies');
  await expect(page.getByRole('link', { name: `${name} v1` })).toHaveCount(0);
});
