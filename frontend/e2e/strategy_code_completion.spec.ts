// Code completion and live type errors in the strategy editor (basedpyright through /ws/strategy-language-server).
import { expect, test, type Page, type TestInfo } from '@playwright/test';

const STRATEGY_CODE = `from nautilus_trader.trading import Strategy


class CompletionStrategy(Strategy):
    def on_start(self) -> None:
        self.subscribe_ba`;

const TYPE_ERROR_CODE = `from nautilus_trader.config import StrategyConfig
from nautilus_trader.trading import Strategy


class EmptyConfig(StrategyConfig):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)


class EmptyStrategy(Strategy):
    pass


count: int = "not a number"
`;

// The first answer of basedpyright includes the analysis of NautilusTrader. A slow CI machine needs more time.
const LANGUAGE_SERVER_TIMEOUT_MILLISECONDS = 30_000;
// More than the 75 ms interactionDelay of @codemirror/autocomplete.
const COMPLETION_INTERACTION_DELAY_MILLISECONDS = 150;

function createUniqueName(currentTest: TestInfo, title: string): string {
  return `${title} ${currentTest.project.name} ${String(Date.now())}`;
}

async function openNewStrategy(page: Page, name: string): Promise<void> {
  await page.goto('/strategies');
  await page.getByRole('button', { name: 'New strategy' }).click();
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

// The status bar "Output" opens the Output tab of the problems and output panel.
async function expectOutputLine(page: Page, text: string): Promise<void> {
  await page.getByRole('button', { name: 'Output', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Output', exact: true }).getByRole('listitem').last()).toContainText(text);
}

test('shows the members of the NautilusTrader Strategy class as completions', async ({ page }, currentTest) => {
  // The client writes each warning and error log of the language server to the console with the prefix "[lsp]".
  const languageServerConsoleMessages: string[] = [];
  page.on('console', (message) => {
    if (message.text().startsWith('[lsp]')) {
      languageServerConsoleMessages.push(message.text());
    }
  });
  await openNewStrategy(page, createUniqueName(currentTest, 'Completion'));

  await replaceCode(page, STRATEGY_CODE);
  await page.keyboard.press('Control+Space');

  await expect(page.getByRole('option', { name: 'subscribe_bars', exact: true })).toBeVisible({
    timeout: LANGUAGE_SERVER_TIMEOUT_MILLISECONDS,
  });
  expect(languageServerConsoleMessages).toEqual([]);
});

test('Tab accepts the selected completion and keeps the focus in the editor', async ({ page }, currentTest) => {
  await openNewStrategy(page, createUniqueName(currentTest, 'Tab completion'));
  const editor = page.getByRole('textbox', { name: 'Strategy code' });

  await replaceCode(page, STRATEGY_CODE);
  await page.keyboard.press('Control+Space');
  await expect(page.getByRole('option', { name: 'subscribe_bars', exact: true })).toBeVisible({
    timeout: LANGUAGE_SERVER_TIMEOUT_MILLISECONDS,
  });
  const selectedName = await page.getByRole('option', { selected: true }).getAttribute('aria-label') ??
    (await page.getByRole('option', { selected: true }).locator('.cm-completionLabel').innerText());
  // CodeMirror ignores an accept for 75 ms (interactionDelay) after the list opens or changes. Then Tab only indents.
  await page.waitForTimeout(COMPLETION_INTERACTION_DELAY_MILLISECONDS);
  await page.keyboard.press('Tab');

  await expect(editor).toContainText(`self.${selectedName}`);
  await expect(editor).toBeFocused();
});

test('shows type errors live and still saves the code', async ({ page }, currentTest) => {
  const name = createUniqueName(currentTest, 'Type error');
  await openNewStrategy(page, name);

  await replaceCode(page, TYPE_ERROR_CODE);

  await expect(page.locator('.cm-lintRange-error')).toHaveCount(1, { timeout: LANGUAGE_SERVER_TIMEOUT_MILLISECONDS });
  await page.getByRole('button', { name: 'Save version' }).click();
  await expectOutputLine(page, `Saved as ${name} v2.`);
});
