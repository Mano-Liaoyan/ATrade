// A failed read on a run page (routes/RunCenter.svelte): the center area shows the reason, and the list keeps its rows.
// The routes and the change socket are fakes, so the test can fail a read at a known time.
import { expect, test, type WebSocketRoute } from '@playwright/test';

const RUN_PAGES = [
  {
    name: 'backtests',
    column: 'Backtests',
    listTitle: 'Backtests not read',
    detailTitle: 'Backtest not read',
    row: { status: 'finished', symbol: 'FAKE', metrics: null },
  },
  {
    name: 'sweeps',
    column: 'Parameter sweeps',
    listTitle: 'Parameter sweeps not read',
    detailTitle: 'Parameter sweep not read',
    row: { status_counts: {}, run_count: 1 },
  },
  {
    name: 'forward-tests',
    column: 'Forward tests',
    listTitle: 'Forward tests not read',
    detailTitle: 'Forward test not read',
    row: { status: 'running', desired_state: 'running', client_id: 10, symbol: 'FAKE' },
  },
];

for (const runPage of RUN_PAGES) {
  test(`a failed read on the ${runPage.name} page shows the reason and keeps the rows`, async ({ page }) => {
    const sockets: WebSocketRoute[] = [];
    await page.routeWebSocket(new RegExp(`/ws/${runPage.name}$`), (socket) => {
      sockets.push(socket);
    });
    await page.route(`**/api/${runPage.name}`, (route) =>
      route.fulfill({ json: [{ id: 9301, strategy_name: 'Fake', version_number: 1, ...runPage.row }] }),
    );
    await page.route(`**/api/${runPage.name}/9301`, (route) => route.fulfill({ status: 500, json: { detail: 'Detail read failed' } }));
    await page.goto(`/${runPage.name}`);

    const row = page.getByRole('complementary', { name: runPage.column, exact: true }).getByRole('link', { name: '#9301', exact: true });
    const main = page.getByRole('main');
    await expect(row).toBeVisible();
    await expect(main.getByText(runPage.detailTitle, { exact: true })).toBeVisible();

    await page.route(`**/api/${runPage.name}`, (route) => route.fulfill({ status: 500, json: { detail: 'List read failed' } }));
    await expect.poll(() => sockets.length).toBeGreaterThan(0);
    for (const socket of sockets) {
      socket.send(JSON.stringify({ type: 'changed' }));
    }

    await expect(main.getByText(runPage.listTitle, { exact: true })).toBeVisible();
    await expect(row).toBeVisible();
  });
}
