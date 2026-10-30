// The "AI assistant" side column of the strategy page (#185, docs/architecture/assistant.md 25.12). The e2e server
// uses the fake assistant service backend/tests/fakes/e2e_assistant.py: the prompt text selects the answer ("wait",
// "change", "backtest", "notitle", or a streamed answer). No real model provider.
import { expect, test, type Locator, type Page, type TestInfo } from '@playwright/test';

// The e2e database is not cleared between tests and browser projects, so each strategy name is unique.
function createUniqueName(currentTest: TestInfo, title: string): string {
  return `AI ${title} ${currentTest.project.name} ${String(Date.now())}`;
}

function assistantColumn(page: Page): Locator {
  return page.getByRole('complementary', { name: 'AI assistant' });
}

function conversationLog(page: Page): Locator {
  return page.getByRole('log', { name: 'Conversation messages' });
}

async function openStrategyWithConversation(page: Page, name: string, height = 900): Promise<void> {
  await page.setViewportSize({ width: 1440, height });
  await page.goto('/strategies');
  await page.getByRole('button', { name: 'New strategy' }).click();
  await page.getByLabel('Strategy name').fill(name);
  await page.getByRole('button', { name: 'Create strategy' }).click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(name);
  const column = assistantColumn(page);
  await column.getByRole('button', { name: 'New conversation' }).click();
  await expect(column.getByRole('combobox', { name: 'Conversation' })).toContainText('New conversation');
  await expect(column.getByText(/^Prompt v\d+$/)).toBeVisible();
  await expect(column.getByRole('button', { name: 'Send' })).toBeEnabled();
}

async function sendMessage(page: Page, text: string): Promise<void> {
  const column = assistantColumn(page);
  await column.getByRole('textbox', { name: 'Message' }).fill(text);
  await column.getByRole('button', { name: 'Send' }).click();
}

async function selectOption(page: Page, name: string, option: string): Promise<void> {
  await assistantColumn(page).getByRole('combobox', { name }).click();
  await page.getByRole('option', { name: option, exact: true }).click();
}

async function expectOutputLine(page: Page, text: string): Promise<void> {
  await expect(page.getByRole('region', { name: 'Output', exact: true }).getByRole('listitem').last()).toContainText(text);
}

test('a prompt streams the answer, which shows its model and credential, and a change applies to the next message', async ({
  page,
}, currentTest) => {
  await openStrategyWithConversation(page, createUniqueName(currentTest, 'Send'));
  const column = assistantColumn(page);
  await expect(column.getByRole('combobox', { name: 'Provider' })).toHaveText('OpenAI');
  await expect(column.getByRole('combobox', { name: 'Model' })).toHaveText('GPT A');
  await expect(column.getByRole('combobox', { name: 'Credential' })).toHaveText('Work key');

  await sendMessage(page, 'Hi.');
  const log = conversationLog(page);
  await expect(log.getByText('Hi.', { exact: true })).toBeVisible();
  await expect(log.getByText('Hello from the fake AI assistant.')).toBeVisible();
  await expect(log.getByText('gpt-a · Work key')).toBeVisible();
  // The generated title replaces "New conversation".
  await expect(column.getByRole('combobox', { name: 'Conversation' })).toHaveText('Title of Hi.');

  await selectOption(page, 'Model', 'GPT B');
  await selectOption(page, 'Credential', 'Home key');
  await sendMessage(page, 'Again.');
  await expect(log.getByText('gpt-b · Home key')).toBeVisible();
  await expect(log.getByText('gpt-a · Work key')).toBeVisible();

  // A reload shows the saved messages.
  await page.reload();
  await expect(conversationLog(page).getByText('gpt-b · Home key')).toBeVisible();
});

test('Send becomes Stop while the AI assistant runs, and Stop ends the run', async ({ page }, currentTest) => {
  await openStrategyWithConversation(page, createUniqueName(currentTest, 'Stop'));
  const column = assistantColumn(page);
  await sendMessage(page, 'Please wait.');
  await expect(conversationLog(page).getByText('Working on it')).toBeVisible();
  const stop = column.getByRole('button', { name: 'Stop' });
  await expect(stop).toBeVisible();
  await stop.click();
  await expect(column.getByRole('button', { name: 'Send' })).toBeVisible();
});

test('a saved version shows a diff card: the card opens CodeDiff, Keep opens the version, Discard keeps the open one', async ({
  page,
}, currentTest) => {
  await openStrategyWithConversation(page, createUniqueName(currentTest, 'Diff'));
  const log = conversationLog(page);
  const versionSelect = page.getByRole('combobox', { name: 'Version' });
  await expect(versionSelect).toHaveText('v1');

  await sendMessage(page, 'Please change the code.');
  await expect(log.getByText('Save strategy version succeeded')).toBeVisible();
  await log.getByRole('button', { name: 'Open the diff of v2' }).click();
  await expect(page.getByRole('tab', { name: 'v1 → v2' })).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByLabel('v2', { exact: true })).toContainText('# Version 2 of the AI assistant.');
  await log.getByRole('button', { name: 'Keep' }).click();
  await expect(versionSelect).toHaveText('v2');
  await expect(log.getByText('Kept', { exact: true })).toBeVisible();

  await sendMessage(page, 'Please change the code again.');
  await expect(log.getByRole('button', { name: 'Open the diff of v3' })).toBeVisible();
  await log.getByRole('button', { name: 'Discard' }).click();
  await expect(log.getByText('Discarded', { exact: true })).toBeVisible();
  await expect(versionSelect).toHaveText('v2');
  await page.getByRole('button', { name: 'Output', exact: true }).click();
  await expectOutputLine(page, 'Discarded');
});

test('a finished backtest shows a tool step and a metric card with a link', async ({ page }, currentTest) => {
  await openStrategyWithConversation(page, createUniqueName(currentTest, 'Backtest'));
  const log = conversationLog(page);
  await sendMessage(page, 'Please run a backtest.');
  await expect(log.getByText(/^Backtest #\d+ finished$/)).toBeVisible();
  const link = log.getByRole('link', { name: /^Backtest #\d+$/ });
  await expect(link).toBeVisible();
  await expect(log.getByText('Total return')).toBeVisible();
  const href = await link.getAttribute('href');
  expect(href).toMatch(/^\/backtests\/\d+$/);
});

test('a title that was not generated writes an Output line with the UTC time', async ({ page }, currentTest) => {
  await openStrategyWithConversation(page, createUniqueName(currentTest, 'Title'));
  await sendMessage(page, 'notitle please');
  // The Output tab opens for an error. Each line starts with the UTC time HH:MM:SS.
  await expect(page.getByRole('region', { name: 'Output', exact: true }).getByRole('listitem').last()).toHaveText(
    /^\d{2}:\d{2}:\d{2}\s+The title was not generated\. The model did not answer\.$/,
  );
});

test('new, rename, and delete conversation; the Credentials and Prompt dialogs open', async ({ page }, currentTest) => {
  await openStrategyWithConversation(page, createUniqueName(currentTest, 'Conversations'));
  const column = assistantColumn(page);
  const conversationSelect = column.getByRole('combobox', { name: 'Conversation' });

  await column.getByRole('button', { name: 'Rename conversation' }).click();
  await page.getByRole('textbox', { name: 'Title' }).fill('My conversation');
  await page.getByRole('button', { name: 'Rename conversation' }).last().click();
  await expect(conversationSelect).toHaveText('My conversation');
  // After a rename, the title does not change.
  await sendMessage(page, 'Hi.');
  await expect(conversationLog(page).getByText('Hello from the fake AI assistant.')).toBeVisible();
  await page.waitForTimeout(1500);
  await expect(conversationSelect).toHaveText('My conversation');

  await column.getByRole('button', { name: 'New conversation' }).click();
  await conversationSelect.click();
  await expect(page.getByRole('option')).toHaveCount(2);
  await page.keyboard.press('Escape');

  await column.getByRole('button', { name: 'Delete conversation' }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByRole('heading')).toContainText('Delete');
  await dialog.getByRole('button', { name: 'Delete conversation' }).click();
  await expect(dialog).toBeHidden();
  await conversationSelect.click();
  await expect(page.getByRole('option')).toHaveCount(1);
  await page.keyboard.press('Escape');

  await column.getByRole('button', { name: 'Credentials' }).click();
  await expect(page.getByRole('dialog', { name: 'Credentials' })).toBeVisible();
  await expect(page.getByRole('dialog').getByText('Work key')).toBeVisible();
  await page.keyboard.press('Escape');
  await column.getByRole('button', { name: 'Prompt' }).click();
  await expect(page.getByRole('dialog').getByRole('button', { name: 'Save as new version' })).toBeVisible();
  await page.keyboard.press('Escape');
});

test('the column is 28rem wide; Minimize gives a rail, Maximize takes the center area, Escape restores', async ({
  page,
}, currentTest) => {
  await openStrategyWithConversation(page, createUniqueName(currentTest, 'Width'));
  const column = assistantColumn(page);
  const readWidth = async (): Promise<number> => Math.round((await column.boundingBox())?.width ?? 0);
  await expect.poll(readWidth).toBe(448);

  await column.getByRole('button', { name: 'Minimize AI assistant' }).click();
  await expect.poll(readWidth).toBe(32);
  await column.getByRole('button', { name: 'Open AI assistant' }).click();
  await expect.poll(readWidth).toBe(448);

  // The strategy list is 17.5rem (280px). The center area is a 32px rail.
  await column.getByRole('button', { name: 'Maximize AI assistant' }).click();
  await expect.poll(readWidth).toBe(1440 - 280 - 32);
  await expect(page.getByRole('heading', { level: 1 })).toBeHidden();
  await column.getByRole('button', { name: 'Restore AI assistant' }).click();
  await expect.poll(readWidth).toBe(448);

  await column.getByRole('button', { name: 'Maximize AI assistant' }).click();
  await expect.poll(readWidth).toBe(1440 - 280 - 32);
  await page.keyboard.press('Escape');
  await expect.poll(readWidth).toBe(448);
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
});

test('the log has a visible scroll track and does not scroll while the user reads older messages', async ({
  page,
}, currentTest) => {
  await openStrategyWithConversation(page, createUniqueName(currentTest, 'Scroll'), 600);
  const log = conversationLog(page);
  for (const number of [1, 2, 3, 4, 5, 6, 7, 8]) {
    await sendMessage(page, `Message ${String(number)}.`);
    await expect(assistantColumn(page).getByRole('button', { name: 'Send' })).toBeVisible();
    await expect(log.getByText(`Message ${String(number)}.`)).toBeVisible();
  }
  await expect.poll(() => log.evaluate((element) => element.scrollHeight > element.clientHeight)).toBe(true);
  const track = page.getByRole('scrollbar', { name: 'Conversation messages scroll bar' });
  await expect(track).toBeVisible();
  await expect(track.locator('.scroll-thumb')).toBeVisible();

  await sendMessage(page, 'Please wait.');
  await expect(log.getByText('Working on it')).toBeVisible();
  await log.evaluate((element) => {
    element.scrollTop = 0;
  });
  await assistantColumn(page).getByRole('button', { name: 'Stop' }).click();
  await expect(assistantColumn(page).getByRole('button', { name: 'Send' })).toBeVisible();
  expect(await log.evaluate((element) => element.scrollTop)).toBe(0);
});
