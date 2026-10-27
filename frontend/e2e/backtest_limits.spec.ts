// Backtest limits: the user changes the timeout and the concurrency on the Backtests page. PostgreSQL stores them.
import { expect, test } from '@playwright/test';

const SAVED_MESSAGE = 'Saved. The limits apply to the next backtest that starts.';

// The browser projects share one database and one backtest queue (e2e/backtest.spec.ts). The test keeps the
// timeout at its default and sets the default concurrency again at the end, so other tests are not affected.
test('changes the backtest limits and sees the saved values', async ({ page }) => {
  await page.goto('/backtests');
  const limitsForm = page.getByRole('form', { name: 'Backtest limits' });
  const limitsStatus = page.getByRole('status', { name: 'Backtest limits status' });
  const timeoutField = limitsForm.getByLabel('Timeout (minutes)');
  const concurrencyField = limitsForm.getByLabel('Backtests at the same time');
  const saveButton = limitsForm.getByRole('button', { name: 'Save limits' });
  await expect(timeoutField).toHaveValue(/^\d+$/);

  await timeoutField.fill('120');
  await concurrencyField.fill('2');
  await saveButton.click();
  await expect(limitsStatus).toHaveText(SAVED_MESSAGE);
  await expect(concurrencyField).toHaveValue('2');

  await concurrencyField.fill('17');
  await saveButton.click();
  await expect(page.getByRole('alert')).toContainText('concurrency');

  await concurrencyField.fill('1');
  await saveButton.click();
  await expect(limitsStatus).toHaveText(SAVED_MESSAGE);
  await expect(timeoutField).toHaveValue('120');
});
