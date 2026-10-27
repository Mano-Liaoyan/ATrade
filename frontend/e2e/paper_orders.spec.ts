// Paper orders by hand with the IBKR fake of backend/tests/e2e_server.py: account DU1234567 and 30 open orders of
// forward test 42. The e2e server keeps its orders between tests, so each test uses its own symbol.
import { expect, test, type Page } from '@playwright/test';

function makeUniqueSymbol(projectName: string): string {
  return `E2E${projectName.slice(0, 2).toUpperCase()}${String(Date.now() % 1_000_000)}`;
}

async function fillLimitOrder(page: Page, symbol: string): Promise<void> {
  const ticket = page.getByRole('form', { name: 'Paper order' });
  await ticket.getByLabel('Order symbol').fill(symbol);
  await ticket.getByLabel('Exchange').fill('NASDAQ');
  await ticket.getByLabel('Currency').fill('USD');
  await ticket.getByLabel('Side').selectOption('BUY');
  await ticket.getByLabel('Quantity').fill('3');
  await ticket.getByLabel('Order type').selectOption('LMT');
  await ticket.getByLabel('Limit price').fill('1.25');
  await ticket.getByLabel('Time in force').selectOption('GTC');
  await ticket.getByRole('button', { name: 'Review order' }).click();
}

test('sends a limit order after the confirmation and cancels it', async ({ page }, currentTest) => {
  const symbol = makeUniqueSymbol(currentTest.project.name);
  await page.goto('/');
  await expect(page.getByRole('status', { name: 'Paper account check' })).toHaveText('Paper account DU1234567 checked.');

  await fillLimitOrder(page, symbol);

  const dialog = page.getByRole('dialog', { name: 'Confirm paper order' });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText('PAPER', { exact: true })).toBeVisible();
  await expect(dialog).toContainText(`${symbol} / NASDAQ / USD`);
  await expect(dialog).toContainText('Buy');
  await expect(dialog).toContainText('Limit, GTC');
  await expect(dialog).toContainText('1.25');
  await expect(dialog).toContainText('DU1234567');
  await dialog.getByRole('button', { name: 'Send paper order' }).click();
  await expect(dialog).toBeHidden();

  const orders = page.getByRole('region', { name: 'Open orders' });
  const orderRow = orders.getByRole('row', { name: new RegExp(symbol) });
  await orderRow.scrollIntoViewIfNeeded();
  await expect(orderRow).toContainText('by hand');
  await expect(orderRow).toContainText('Submitted');
  await orderRow.getByRole('button', { name: /Cancel order/ }).click();
  await expect(orderRow).toHaveCount(0);
});

test('sends no order when the user goes back from the confirmation', async ({ page }, currentTest) => {
  const symbol = makeUniqueSymbol(currentTest.project.name);
  await page.goto('/');
  await expect(page.getByRole('status', { name: 'Paper account check' })).toHaveText('Paper account DU1234567 checked.');

  await fillLimitOrder(page, symbol);
  const dialog = page.getByRole('dialog', { name: 'Confirm paper order' });
  await dialog.getByRole('button', { name: 'Back' }).click();

  await expect(dialog).toBeHidden();
  await expect(page.getByRole('region', { name: 'Open orders' }).getByRole('row', { name: new RegExp(symbol) })).toHaveCount(0);
});

test('shows forward test orders without a cancel button', async ({ page }) => {
  await page.goto('/');
  const orderRow = page.getByRole('region', { name: 'Open orders' }).getByRole('row', { name: /FTO01/ });

  await expect(orderRow).toContainText('forward test 42');
  await expect(orderRow.getByRole('button')).toHaveCount(0);
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
