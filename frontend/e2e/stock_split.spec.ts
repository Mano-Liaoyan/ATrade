// The "Split check needed" state (docs/architecture/paper_trading.md section 11.11). backend/tests/e2e_split_checks.py
// gives each browser project its own instrument, for example SPCHRO for chromium: IBKR shows 40 shares, a stopped
// forward test holds 10 in the owner ledger, and the check found a 4:1 ratio from the position only.
import { expect, test, type Page } from '@playwright/test';

// The same rule as make_split_symbol of backend/tests/e2e_split_checks.py.
function makeSplitSymbol(projectName: string): string {
  return `SP${projectName.slice(0, 4).toUpperCase()}`;
}

async function findForwardTestId(page: Page, symbol: string): Promise<number> {
  const response = await page.request.get('/api/forward-tests');
  const forwardTests = (await response.json()) as { id: number; symbol: string | null }[];
  const forwardTest = forwardTests.find((item) => item.symbol === symbol);
  if (forwardTest === undefined) {
    throw new Error(`The e2e server has no forward test of ${symbol}.`);
  }
  return forwardTest.id;
}

test('the split check shows on the 3 pages and Apply split 4:1 ends it', async ({ page }, currentTest) => {
  const symbol = makeSplitSymbol(currentTest.project.name);
  const forwardTestId = await findForwardTestId(page, symbol);

  // The forward test page: the header line names the instrument.
  await page.goto(`/forward-tests/${String(forwardTestId)}`);
  const chartPanel = page.getByRole('region', { name: `Forward test #${String(forwardTestId)}` });
  const headerWarning = chartPanel.getByText(`Split check needed: ${symbol}`);
  await expect(headerWarning).toBeVisible();
  await expect(chartPanel.locator('.status-indicator--warning svg').first()).toBeAttached();

  // The instrument page: the review button is disabled and the panel says why.
  await page.goto(`/instruments/NASDAQ/${symbol}?currency=USD`);
  const panel = page.getByRole('form', { name: `Paper order of ${symbol}`, exact: true });
  await expect(panel.getByRole('button', { name: 'Review buy order' })).toBeDisabled();
  await expect(panel).toContainText(
    `${symbol} needs a split check. Apply the split or keep the ledger on the paper trading page.`,
  );

  // The paper trading page: the Positions row with the ratio, the IBKR share counts, and the 2 buttons.
  await page.goto('/');
  const positions = page.getByRole('region', { name: 'Positions', exact: true }).first();
  const splitRow = positions.getByRole('row', { name: /Split check needed/ }).filter({ hasText: symbol });
  await expect(splitRow).toContainText('Split check needed: 4:1');
  await expect(splitRow).toContainText('10 → 40');
  await expect(splitRow.locator('.status-indicator--warning svg')).toBeAttached();
  await expect(splitRow.getByRole('button', { name: 'Keep ledger' })).toBeVisible();
  await splitRow.getByRole('button', { name: 'Apply split 4:1' }).click();
  await expect(splitRow).toHaveCount(0);
  await expect(positions.getByRole('row', { name: new RegExp(symbol) }).first()).toContainText(
    `Forward test ${String(forwardTestId)}`,
  );

  // The Fills table: the fill and the split adjustment row.
  await page.goto(`/forward-tests/${String(forwardTestId)}`);
  await expect(page.getByText(`Split check needed: ${symbol}`)).toHaveCount(0);
  const fills = page.getByRole('region', { name: 'Forward test tables' }).getByRole('region', { name: 'Fills' });
  const splitFill = fills.getByRole('row', { name: /Split 4:1/ });
  await expect(splitFill.getByRole('cell')).toHaveText([
    /\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC/,
    symbol,
    'Split 4:1',
    '+30',
    '',
    '',
    '0.00',
  ]);
});
