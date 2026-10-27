// Paper orders by hand with the IBKR fake of backend/tests/e2e_server.py: account DU1234567 and 30 open orders of
// forward test 42. The e2e server keeps its orders between tests, so each test uses its own symbol.
import { expect, test, type Page } from '@playwright/test';

function makeUniqueSymbol(projectName: string): string {
  return `E2E${projectName.slice(0, 2).toUpperCase()}${String(Date.now() % 1_000_000)}`;
}

async function selectOption(page: Page, selectName: string, optionName: string): Promise<void> {
  await page.getByRole('form', { name: 'Paper order' }).getByRole('combobox', { name: selectName }).click();
  await page.getByRole('option', { name: optionName }).click();
}

async function fillLimitOrder(page: Page, symbol: string): Promise<void> {
  const ticket = page.getByRole('form', { name: 'Paper order' });
  await ticket.getByRole('tab', { name: 'Buy' }).click();
  await ticket.getByLabel('Order symbol').fill(symbol);
  await ticket.getByLabel('Exchange').fill('NASDAQ');
  await ticket.getByLabel('Currency').fill('USD');
  await ticket.getByLabel('Quantity').fill('3');
  await selectOption(page, 'Order type', 'Limit');
  await ticket.getByLabel('Limit price').fill('1.25');
  await selectOption(page, 'Time in force', 'GTC');
  await ticket.getByRole('button', { name: 'Review order' }).click();
}

test('sends a limit order after the confirmation and cancels it', async ({ page }, currentTest) => {
  const symbol = makeUniqueSymbol(currentTest.project.name);
  await page.goto('/');
  await expect(page.getByRole('status', { name: 'Paper account check' })).toHaveText('Paper account DU1234567 checked.');

  await fillLimitOrder(page, symbol);

  const dialog = page.getByRole('dialog', { name: `Buy 3 ${symbol}` });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText('PAPER', { exact: true })).toBeVisible();
  await expect(dialog).toContainText(`${symbol} / NASDAQ / USD`);
  await expect(dialog).toContainText('Buy');
  await expect(dialog).toContainText('Limit, GTC');
  await expect(dialog).toContainText('1.25');
  await expect(dialog).toContainText('DU1234567');
  await dialog.getByRole('button', { name: 'Send paper order' }).click();
  await expect(dialog).toBeHidden();
  const sentNotification = page.getByRole('status').filter({ hasText: /Order \d+ sent/ });
  await expect(sentNotification).toBeVisible();
  await sentNotification.getByRole('button', { name: 'Close notification' }).click();
  await expect(sentNotification).toHaveCount(0);

  const orders = page.getByRole('region', { name: 'Open orders' });
  const orderRow = orders.getByRole('row', { name: new RegExp(symbol) });
  await orderRow.scrollIntoViewIfNeeded();
  await expect(orderRow).toContainText('by hand');
  await expect(orderRow).toContainText('Submitted');
  await orderRow.getByRole('button', { name: /^Actions for order \d+$/ }).click();
  await page.getByRole('menuitem', { name: 'Cancel order' }).click();
  await expect(page.getByRole('menu')).toHaveCount(0);
  await expect(page.getByRole('status').filter({ hasText: /Cancel request sent for order \d+/ })).toBeVisible();
  await expect(orderRow).toHaveCount(0);
});

test('cancels an open order with the keyboard only', async ({ page }, currentTest) => {
  const symbol = makeUniqueSymbol(currentTest.project.name);
  await page.goto('/');
  await expect(page.getByRole('status', { name: 'Paper account check' })).toHaveText('Paper account DU1234567 checked.');
  await fillLimitOrder(page, symbol);
  const dialog = page.getByRole('dialog', { name: `Buy 3 ${symbol}` });
  await dialog.getByRole('button', { name: 'Send paper order' }).click();
  await expect(dialog).toBeHidden();

  const orderRow = page.getByRole('region', { name: 'Open orders' }).getByRole('row', { name: new RegExp(symbol) });
  await expect(orderRow).toContainText('Submitted');
  // The keyboard opens the row overflow menu, moves to the enabled item, and chooses it.
  await orderRow.getByRole('button', { name: /^Actions for order \d+$/ }).focus();
  await page.keyboard.press('Space');
  const cancelItem = page.getByRole('menuitem', { name: 'Cancel order' });
  await expect(cancelItem).toBeFocused();
  await expect(cancelItem).toBeEnabled();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('menu')).toHaveCount(0);
  await expect(page.getByRole('status').filter({ hasText: /Cancel request sent for order \d+/ })).toBeVisible();
  await expect(orderRow).toHaveCount(0);
});

test('sends no order when the user goes back from the confirmation', async ({ page }, currentTest) => {
  const symbol = makeUniqueSymbol(currentTest.project.name);
  await page.goto('/');
  await expect(page.getByRole('status', { name: 'Paper account check' })).toHaveText('Paper account DU1234567 checked.');

  await fillLimitOrder(page, symbol);
  const dialog = page.getByRole('dialog', { name: `Buy 3 ${symbol}` });
  await dialog.getByRole('button', { name: 'Cancel' }).click();

  await expect(dialog).toBeHidden();
  await expect(page.getByRole('region', { name: 'Open orders' }).getByRole('row', { name: new RegExp(symbol) })).toHaveCount(0);
});

test('the confirmation keeps the focus, closes with Escape, and gives the focus back', async ({ page }, currentTest) => {
  const symbol = makeUniqueSymbol(currentTest.project.name);
  await page.goto('/');
  await expect(page.getByRole('status', { name: 'Paper account check' })).toHaveText('Paper account DU1234567 checked.');

  await fillLimitOrder(page, symbol);
  const dialog = page.getByRole('dialog', { name: `Buy 3 ${symbol}` });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole('button', { name: 'Send paper order' })).toBeVisible();

  // Tab goes round the controls of the dialog and does not leave it.
  for (let pressCount = 0; pressCount < 5; pressCount += 1) {
    await page.keyboard.press('Tab');
    await expect(dialog.locator(':focus')).toHaveCount(1);
  }
  await page.keyboard.press('Escape');

  await expect(dialog).toBeHidden();
  await expect(page.getByRole('button', { name: 'Review order' })).toBeFocused();
  await expect(page.getByRole('region', { name: 'Open orders' }).getByRole('row', { name: new RegExp(symbol) })).toHaveCount(0);
});

test('the side, order type, and time in force work with the keyboard', async ({ page }) => {
  await page.goto('/');
  const ticket = page.getByRole('form', { name: 'Paper order' });
  const buy = ticket.getByRole('tab', { name: 'Buy' });
  const sell = ticket.getByRole('tab', { name: 'Sell' });
  await expect(buy).toHaveAttribute('aria-selected', 'true');

  await buy.focus();
  await page.keyboard.press('ArrowRight');
  await expect(sell).toBeFocused();
  await expect(sell).toHaveAttribute('aria-selected', 'true');
  await page.keyboard.press('ArrowLeft');
  await expect(buy).toHaveAttribute('aria-selected', 'true');

  const orderType = ticket.getByRole('combobox', { name: 'Order type' });
  await expect(orderType).toHaveText('Limit');
  await orderType.focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('listbox')).toBeVisible();
  await page.keyboard.press('ArrowDown');
  await page.keyboard.press('Enter');
  await expect(page.getByRole('listbox')).toBeHidden();
  await expect(orderType).toHaveText('Market');
  await expect(ticket.getByLabel('Limit price')).toHaveCount(0);

  const timeInForce = ticket.getByRole('combobox', { name: 'Time in force' });
  await timeInForce.focus();
  await page.keyboard.press('ArrowDown');
  await expect(page.getByRole('listbox')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('listbox')).toBeHidden();
  await expect(timeInForce).toHaveText('DAY');
  await expect(timeInForce).toBeFocused();
});

test('disables the cancel item of a forward test order and says why', async ({ page }) => {
  await page.goto('/');
  const orderRow = page.getByRole('region', { name: 'Open orders' }).getByRole('row', { name: /FTO01/ });
  await expect(orderRow).toContainText('forward test 42');

  await orderRow.getByRole('button', { name: /^Actions for order \d+$/ }).focus();
  await page.keyboard.press('Enter');
  const cancelItem = page.getByRole('menuitem', { name: 'Stop forward test 42 to cancel' });
  await expect(cancelItem).toBeVisible();
  await expect(cancelItem).toHaveAttribute('aria-disabled', 'true');
  await page.keyboard.press('Escape');
  await expect(page.getByRole('menu')).toHaveCount(0);
  await expect(orderRow).toBeAttached();
});

test('the overflow menu of the last open order is not clipped by the scroll region', async ({ page }) => {
  await page.goto('/');
  const orders = page.getByRole('region', { name: 'Open orders' });
  const lastRow = orders.getByRole('row').last();
  await orders.scrollIntoViewIfNeeded();
  await page.getByRole('scrollbar', { name: 'Open orders scroll bar' }).focus();
  await page.keyboard.press('End');
  await expect(lastRow).toBeInViewport();

  await lastRow.getByRole('button', { name: /^Actions for order \d+$/ }).click();
  const menu = page.getByRole('menu');
  await expect(menu).toBeVisible();
  // The menu content is under <body>, outside the scroll region, so the region cannot clip it.
  await expect(orders.getByRole('menu')).toHaveCount(0);
  await expect(menu.getByRole('menuitem')).toBeInViewport({ ratio: 1 });
});

test('order list has a visible scroll track and its last row can be scrolled into view', async ({ page }) => {
  await page.goto('/');
  const orders = page.getByRole('region', { name: 'Open orders' });
  const firstRow = orders.getByRole('row', { name: /FTO01/ });
  const lastRow = orders.getByRole('row').last();
  const track = page.getByRole('scrollbar', { name: 'Open orders scroll bar' });
  await expect(firstRow).toBeAttached();
  await orders.scrollIntoViewIfNeeded();

  await expect(firstRow).toBeInViewport();
  await expect(track).toBeVisible();
  await expect(track.locator('.scroll-thumb')).toBeVisible();
  await expect(lastRow).not.toBeInViewport();

  await track.focus();
  await page.keyboard.press('End');

  await expect(lastRow).toBeInViewport();
  await expect(track).toHaveAttribute('aria-valuenow', '100');
});
