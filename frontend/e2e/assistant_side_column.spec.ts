// The "AI assistant" side column of each workbench page (#185, docs/architecture/assistant.md 25.12). The e2e server
// uses the fake assistant service backend/tests/fakes/e2e_assistant.py: the prompt text selects the answer ("wait",
// "screen", "change", "backtest", "notitle", "markdown", or a streamed answer). No real model provider.
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

  // GPT B has thinking levels: the line shows the default level "medium" of pi.
  await selectOption(page, 'Model', 'GPT B');
  await selectOption(page, 'Credential', 'Home key');
  await sendMessage(page, 'Again.');
  await expect(log.getByText('gpt-b · medium · Home key')).toBeVisible();
  await expect(log.getByText('gpt-a · Work key')).toBeVisible();

  // A reload shows the saved messages.
  await page.reload();
  await expect(conversationLog(page).getByText('gpt-b · medium · Home key')).toBeVisible();
});

test('the Model list shows the full model names, and the chosen thinking level is sent and shown', async ({
  page,
}, currentTest) => {
  await openStrategyWithConversation(page, createUniqueName(currentTest, 'Thinking'));
  const column = assistantColumn(page);
  const thinking = column.getByRole('combobox', { name: 'Thinking' });
  // GPT A has no reasoning: the Select is disabled and says why.
  await expect(thinking).toBeDisabled();
  await expect(thinking).toHaveText('No thinking');
  await expect(thinking).toHaveAccessibleDescription('The model has no thinking levels.');

  await column.getByRole('combobox', { name: 'Model' }).click();
  const longOption = page.getByRole('option', { name: 'GPT Long Context Reasoning Preview Edition', exact: true });
  await expect(longOption).toBeVisible();
  const isCut = await longOption
    .locator('.cds--list-box__menu-item__option')
    .evaluate((element) => element.scrollWidth > element.clientWidth);
  expect(isCut).toBe(false);
  await longOption.click();

  await expect(thinking).toBeEnabled();
  await expect(thinking).toHaveText('Medium');
  await selectOption(page, 'Thinking', 'High');
  await sendMessage(page, 'Think about it.');
  const log = conversationLog(page);
  await expect(log.getByText('gpt-long · high · Work key')).toBeVisible();

  // The browser keeps the chosen level.
  await page.reload();
  await expect(conversationLog(page).getByText('gpt-long · high · Work key')).toBeVisible();
  await expect(assistantColumn(page).getByRole('combobox', { name: 'Thinking' })).toHaveText('High');
});

test('an answer shows its markdown: heading, bold, table, shell command, diff, and Mermaid diagram', async ({
  page,
  context,
  browserName,
}, currentTest) => {
  await openStrategyWithConversation(page, createUniqueName(currentTest, 'Markdown'));
  await sendMessage(page, 'Show markdown.');
  const log = conversationLog(page);

  await expect(log.getByRole('heading', { name: 'Backtest summary', level: 3 })).toBeVisible();
  await expect(log.locator('strong', { hasText: 'higher Sharpe ratio' })).toBeVisible();
  await expect(log.getByText('**')).toHaveCount(0);

  const table = log.getByRole('table');
  await expect(table.getByRole('columnheader', { name: 'Return' })).toBeVisible();
  await expect(table.getByRole('cell', { name: '12.5%' })).toHaveAttribute('align', 'right');
  await expect(table.getByRole('cell', { name: 'MSFT' })).toBeVisible();

  const shell = log.getByRole('figure', { name: 'bash' });
  await expect(shell).toContainText('pnpm install');
  if (browserName === 'chromium') {
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);
    await shell.getByRole('button', { name: 'Copy' }).click();
    await expect(shell.getByRole('button', { name: 'Copied' })).toBeVisible();
    expect(await page.evaluate(() => navigator.clipboard.readText())).toBe('pnpm install');
  } else {
    await expect(shell.getByRole('button', { name: 'Copy' })).toBeVisible();
  }

  const diff = log.getByRole('figure', { name: 'diff' });
  await expect(diff).toContainText('threshold = 25');
  await expect(diff).toContainText('threshold = 30');

  const diagram = log.getByRole('figure', { name: 'Mermaid diagram' });
  await expect(diagram.locator('svg')).toBeVisible();
  await expect(diagram.locator('svg')).toContainText('Backtest');
  await expect(log.getByText('flowchart LR')).toHaveCount(0);
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

test('a saved screen shows a condition card with each change mark; Keep and Discard become states; Open screen opens it', async ({
  page,
  request,
}, currentTest) => {
  await openStrategyWithConversation(page, createUniqueName(currentTest, 'Screen'));
  const log = conversationLog(page);
  await sendMessage(page, 'Make a screen.');
  await expect(log.getByText('I saved a new screen.')).toBeVisible();
  const kept = log.getByRole('article', { name: /^Screen E2E momentum/ }).first();
  await expect(kept.getByText('US', { exact: true })).toBeVisible();
  const conditions = kept.getByRole('list', { name: 'Conditions' });
  await expect(conditions.getByRole('img', { name: 'Changed' })).toHaveCount(1);
  await expect(conditions.getByRole('img', { name: 'Removed' })).toHaveCount(1);
  await expect(conditions.getByRole('img', { name: 'Added' })).toHaveCount(1);
  // The changed value: the old value with a line through it, then the new value.
  const changed = conditions.locator('.condition-tag', { has: page.getByRole('img', { name: 'Changed' }) });
  await expect(changed).toHaveText(/^\s*Close\s*>\s*5\s*20\s*$/);
  await expect(changed.locator('s')).toHaveText('5');
  await expect(conditions.getByLabel('Order count')).toHaveText('20');

  await kept.getByRole('button', { name: 'Keep' }).click();
  await expect(kept.getByText('Kept')).toBeVisible();
  await expect(kept.getByRole('button', { name: 'Keep' })).toHaveCount(0);
  await expect(kept.getByRole('button', { name: 'Discard' })).toHaveCount(0);
  const keptHref = await kept.getByRole('link', { name: 'Open screen' }).getAttribute('href');
  const keptRead = await request.get(`/api${keptHref ?? ''}`);
  expect(((await keptRead.json()) as { kept: boolean }).kept).toBe(true);

  await sendMessage(page, 'Make another screen.');
  await expect(log.getByRole('article', { name: /^Screen E2E momentum/ })).toHaveCount(2);
  const discarded = log.getByRole('article', { name: /^Screen E2E momentum/ }).last();
  const discardedHref = await discarded.getByRole('link', { name: 'Open screen' }).getAttribute('href');
  await discarded.getByRole('button', { name: 'Discard' }).click();
  await expect(discarded.getByText('Discarded')).toBeVisible();
  await expect(discarded.getByRole('button')).toHaveCount(0);
  expect((await request.get(`/api${discardedHref ?? ''}`)).status()).toBe(404);

  await kept.getByRole('link', { name: 'Open screen' }).click();
  await expect(page).toHaveURL(new RegExp(`${keptHref ?? ''}$`));
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

  // All pages list all conversations, and the other tests add conversations too, so the title is unique.
  const title = createUniqueName(currentTest, 'My conversation');
  await column.getByRole('button', { name: 'Rename conversation' }).click();
  await page.getByRole('textbox', { name: 'Title' }).fill(title);
  await page.getByRole('button', { name: 'Rename conversation' }).last().click();
  await expect(conversationSelect).toHaveText(title);
  // After a rename, the title does not change.
  await sendMessage(page, 'Hi.');
  await expect(conversationLog(page).getByText('Hello from the fake AI assistant.')).toBeVisible();
  await page.waitForTimeout(1500);
  await expect(conversationSelect).toHaveText(title);

  const created = page.waitForResponse(
    (response) => response.url().endsWith('/api/assistant/conversations') && response.request().method() === 'POST',
  );
  await column.getByRole('button', { name: 'New conversation' }).click();
  const { id: newId } = (await (await created).json()) as { id: number };
  await expect(conversationSelect).toContainText('New conversation');
  await conversationSelect.click();
  await expect(page.getByRole('option', { name: title, exact: true })).toHaveCount(1);
  await page.keyboard.press('Escape');

  await column.getByRole('button', { name: 'Delete conversation' }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByRole('heading')).toContainText('Delete');
  await dialog.getByRole('button', { name: 'Delete conversation' }).click();
  await expect(dialog).toBeHidden();
  expect((await page.request.get(`/api/assistant/conversations/${String(newId)}`)).status()).toBe(404);
  await conversationSelect.click();
  await expect(page.getByRole('option', { name: title, exact: true })).toHaveCount(1);
  await page.keyboard.press('Escape');

  await column.getByRole('button', { name: 'Credentials' }).click();
  await expect(page.getByRole('dialog', { name: 'Credentials' })).toBeVisible();
  await expect(page.getByRole('dialog').getByText('Work key')).toBeVisible();
  // The provider list is longer than the dialog. The dialog content does not cut it: the bottom of the list gets the hit.
  await page.getByRole('dialog').getByRole('combobox', { name: 'Provider' }).click();
  const providerList = page.getByRole('listbox');
  await expect(providerList.getByRole('option', { name: 'Subscription 1', exact: true })).toBeVisible();
  expect(
    await providerList.evaluate((list) => {
      const box = list.getBoundingClientRect();
      return list.contains(document.elementFromPoint(box.left + box.width / 2, box.bottom - 4));
    }),
  ).toBe(true);
  await page.keyboard.press('Escape');
  await page.keyboard.press('Escape');
  await column.getByRole('button', { name: 'Prompt' }).click();
  await expect(page.getByRole('dialog').getByRole('button', { name: 'Save as new version' })).toBeVisible();
  await page.getByRole('dialog').getByRole('button', { name: 'Close' }).click();
  await expect(page.getByRole('dialog')).toBeHidden();
  await expect(column.getByRole('button', { name: 'Prompt' })).toBeVisible();
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
    await expect(log.getByText(`Message ${String(number)}.`)).toBeVisible();
    // Send is visible also before the run starts. Wait for the answer, so that the next click is not on Stop.
    await expect(log.getByText('Hello from the fake AI assistant.')).toHaveCount(number);
    await expect(assistantColumn(page).getByRole('button', { name: 'Send' })).toBeVisible();
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

async function openPage(page: Page, name: string, url: RegExp): Promise<void> {
  await page.getByRole('navigation', { name: 'Pages' }).getByRole('link', { name }).click();
  await expect(page).toHaveURL(url);
}

test('each workbench page has the column with the same conversations, and the open conversation stays across pages', async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/screens');
  const column = assistantColumn(page);
  const conversationSelect = column.getByRole('combobox', { name: 'Conversation' });
  // A page without an open strategy starts a conversation without a strategy.
  await column.getByRole('button', { name: 'New conversation' }).click();
  await expect(conversationSelect).toContainText('New conversation');
  await sendMessage(page, 'Hi.');
  await expect(conversationLog(page).getByText('Hello from the fake AI assistant.')).toBeVisible();
  await expect(conversationSelect).toHaveText('Title of Hi.');

  await openPage(page, 'Backtests', /\/backtests/);
  await expect(conversationSelect).toHaveText('Title of Hi.');
  await expect(conversationLog(page).getByText('Hi.', { exact: true })).toBeVisible();
  await sendMessage(page, 'Again.');
  await expect(conversationLog(page).getByText('Hello from the fake AI assistant.')).toHaveCount(2);

  // Minimize stays across pages.
  await column.getByRole('button', { name: 'Minimize AI assistant' }).click();
  await openPage(page, 'Parameter sweeps', /\/sweeps/);
  await column.getByRole('button', { name: 'Open AI assistant' }).click();
  await expect(conversationSelect).toHaveText('Title of Hi.');
  await openPage(page, 'Forward tests', /\/forward-tests/);
  await expect(conversationSelect).toHaveText('Title of Hi.');
  await expect(conversationLog(page).getByText('Again.', { exact: true })).toBeVisible();
  await openPage(page, 'Strategies', /\/strategies/);
  await expect(conversationSelect).toHaveText('Title of Hi.');
});

test('a page without an Output tab shows the errors of the conversation in the column', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/backtests');
  const column = assistantColumn(page);
  await column.getByRole('button', { name: 'New conversation' }).click();
  await expect(column.getByRole('combobox', { name: 'Conversation' })).toContainText('New conversation');
  await sendMessage(page, 'notitle please');
  await expect(column.getByText('The title was not generated. The model did not answer.')).toBeVisible();
});

test('Maximize of the column makes the center area of the screen page a rail', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/screens');
  const column = assistantColumn(page);
  const readWidth = async (): Promise<number> => Math.round((await column.boundingBox())?.width ?? 0);
  await expect.poll(readWidth).toBe(448);
  await column.getByRole('button', { name: 'Maximize AI assistant' }).click();
  // The screen list is 20rem (320px). The center area is a 32px rail.
  await expect.poll(readWidth).toBe(1440 - 320 - 32);
  await page.keyboard.press('Escape');
  await expect.poll(readWidth).toBe(448);
});
