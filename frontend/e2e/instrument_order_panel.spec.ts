// The order panel of the instrument page (#103), IBKR Desktop layout: the Buy / Sell switch, the order fields, the
// order and account numbers in two columns, and the full-width button. The order is for the instrument of the page.
// Against the real backend with the IBKR fake (backend/tests/e2e_server.py): account DU1234567, cash 25,000.00 USD,
// net liquidation 101,234.50 USD, and a position of 10 TEST01 at 100.00.
import { expect, test, type Locator, type Page } from '@playwright/test';

const PAGE_PATH = '/instruments/SEHK/700?currency=HKD&bar_period=1-HOUR';
const CHART_NAME = 'Bar chart of 700 / SEHK / HKD, 1-HOUR bars';

function orderPanel(page: Page, symbol = '700'): Locator {
  return page.getByRole('form', { name: `Paper order of ${symbol}`, exact: true });
}

function keyNumber(panel: Locator, name: string): Locator {
  return panel.locator('dt', { hasText: name }).locator('xpath=following-sibling::dd[1]');
}

async function openWorkbench(page: Page): Promise<void> {
  await page.goto(PAGE_PATH);
  await expect(page.getByRole('status', { name: 'Bar count' })).toHaveText('2160 bars');
}

test('the order panel is for the instrument of the page and starts with the last price', async ({ page }) => {
  await openWorkbench(page);
  const panel = orderPanel(page);

  await expect(panel.getByRole('tab', { name: 'Buy' })).toHaveAttribute('aria-selected', 'true');
  await expect(panel.getByLabel('Order symbol')).toHaveCount(0);
  await expect(panel.getByLabel('Limit price')).toHaveValue(/^\d+\.\d{2}$/);
  const limitPrice = Number(await panel.getByLabel('Limit price').inputValue());

  await panel.getByLabel('Quantity').fill('2');
  await expect(keyNumber(panel, 'Order value')).toHaveText(
    (2 * limitPrice).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
  );
  await expect(keyNumber(panel, 'Position')).toHaveText('0');
  await expect(keyNumber(panel, 'Cash (USD)')).toHaveText('25,000.00');
  await expect(keyNumber(panel, 'Net liquidation (USD)')).toHaveText('101,234.50');

  const button = panel.getByRole('button', { name: 'Review buy order' });
  await expect(button).toBeEnabled();
  await expect(button).toHaveClass(/cds--btn--primary/);
  await panel.getByRole('tab', { name: 'Sell' }).click();
  await expect(panel.getByRole('button', { name: 'Review sell order' })).toHaveClass(/cds--btn--danger/);
});

test('the order panel shows the position of the instrument', async ({ page }) => {
  await page.goto('/instruments/NASDAQ/TEST01?currency=USD');
  const panel = orderPanel(page, 'TEST01');

  await expect(keyNumber(panel, 'Position')).toHaveText('10');
  await expect(keyNumber(panel, 'Average cost')).toHaveText('100.00');
  await expect(keyNumber(panel, 'Unrealized P&L')).toHaveText('0.00');
});

test('a sent paper order shows in the open orders panel', async ({ page }) => {
  await openWorkbench(page);
  const panel = orderPanel(page);
  await panel.getByLabel('Quantity').fill('2');
  await panel.getByLabel('Limit price').fill('1.25');
  await panel.getByRole('button', { name: 'Review buy order' }).click();

  const dialog = page.getByRole('dialog', { name: 'Buy 2 700' });
  await expect(dialog.getByText('PAPER', { exact: true })).toBeVisible();
  await expect(dialog).toContainText('700 / SEHK / HKD');
  await expect(dialog).toContainText('Limit, DAY');
  await dialog.getByRole('button', { name: 'Send paper order' }).click();
  await expect(dialog).toBeHidden();
  const sentNotification = panel.getByRole('status').filter({ hasText: /Order \d+ sent/ });
  await expect(sentNotification).toBeVisible();
  const orderId = /Order (\d+) sent/.exec((await sentNotification.textContent()) ?? '')?.[1] ?? '';

  await page.getByRole('region', { name: 'Paper account' }).getByRole('tab', { name: /^Open orders/ }).click();
  const actions = page.getByRole('button', { name: `Actions for order ${orderId}` });
  const orderRow = page.getByRole('region', { name: 'Open orders' }).getByRole('row').filter({ has: actions });
  await expect(orderRow).toContainText('700');
  await expect(orderRow).toContainText('by hand');

  // The e2e server keeps its orders: cancel the order again.
  await actions.click();
  await page.getByRole('menuitem', { name: 'Cancel order' }).click();
  await expect(orderRow).toHaveCount(0);
});

test('the chart rescales when the order column minimizes and opens', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await openWorkbench(page);
  const chart = page.getByRole('img', { name: CHART_NAME });
  const readWidth = async (): Promise<number> => (await chart.boundingBox())?.width ?? 0;
  const firstWidth = await readWidth();

  await page.getByRole('button', { name: 'Minimize paper order' }).click();
  await expect(orderPanel(page)).toBeHidden();
  await expect.poll(readWidth).toBeGreaterThan(firstWidth + 100);

  await page.getByRole('button', { name: 'Open paper order' }).click();
  await expect(orderPanel(page)).toBeVisible();
  await expect.poll(readWidth).toBeLessThan(firstWidth + 1);
});

test('a failed paper account check disables the button and says why', async ({ page }) => {
  // The page gets a failed paper account check from a fake /ws/paper-trading socket.
  await page.routeWebSocket(/\/ws\/paper-trading$/, (socket) => {
    socket.send(
      JSON.stringify({
        type: 'account',
        check: { status: 'failed', message: 'Wrong account.', actual_accounts: ['U1'], expected_account: 'DU1234567' },
        balance: null,
        positions: [],
      }),
    );
  });
  await openWorkbench(page);

  const button = orderPanel(page).getByRole('button', { name: 'Review buy order' });
  await expect(button).toBeDisabled();
  await expect(button).toHaveAccessibleDescription('Paper account check failed. ATrade sends no orders.');
});
