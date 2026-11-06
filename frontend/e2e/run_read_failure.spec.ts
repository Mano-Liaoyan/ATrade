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

const FAKE_SWEEP = {
  id: 9302,
  strategy_version_id: 1,
  strategy_id: 1,
  strategy_name: 'Fake',
  version_number: 1,
  grid: [{ name: 'fast_period', values: [10] }],
  created_at_utc: '2026-01-02T03:04:05Z',
  run_count: 0,
  status_counts: {},
};

test('the delete of the last parameter sweep shows the empty state, not a failed read', async ({ page }) => {
  let isDeleted = false;
  let socket: WebSocketRoute | undefined;
  let finishDetailRead = (): void => undefined;
  const detailReadAfterDelete = new Promise<void>((resolve) => {
    finishDetailRead = resolve;
  });
  await page.routeWebSocket(/\/ws\/sweeps$/, (route) => {
    socket = route;
  });
  await page.route('**/api/sweeps', (route) => route.fulfill({ json: isDeleted ? [] : [FAKE_SWEEP] }));
  await page.route('**/api/sweeps/9302', async (route) => {
    if (route.request().method() === 'DELETE') {
      // The change push comes before the answer of the delete, so the page reads the deleted sweep.
      isDeleted = true;
      socket?.send(JSON.stringify({ type: 'changed' }));
      await detailReadAfterDelete;
      await route.fulfill({ status: 204 });
    } else if (isDeleted) {
      await route.fulfill({ status: 404, json: { detail: 'Parameter sweep not found' } });
      finishDetailRead();
    } else {
      await route.fulfill({ json: { ...FAKE_SWEEP, runs: [] } });
    }
  });
  await page.goto('/sweeps/9302');

  await page.getByRole('button', { name: 'Delete parameter sweep' }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Delete parameter sweep' }).click();

  await expect(page).toHaveURL(/\/sweeps$/);
  await expect(page.getByRole('main').getByText('No parameter sweeps', { exact: true })).toBeVisible();
  await expect(page.getByText('Parameter sweep not read', { exact: true })).toHaveCount(0);
});

test('a list read from before the delete does not open the deleted parameter sweep', async ({ page }) => {
  let finishListRead = (): void => undefined;
  const listRead = new Promise<void>((resolve) => {
    finishListRead = resolve;
  });
  await page.routeWebSocket(/\/ws\/sweeps$/, () => undefined);
  await page.route('**/api/sweeps', async (route) => {
    await listRead;
    await route.fulfill({ json: [FAKE_SWEEP] });
  });
  await page.route('**/api/sweeps/9302', (route) =>
    route.request().method() === 'DELETE' ? route.fulfill({ status: 204 }) : route.fulfill({ json: { ...FAKE_SWEEP, runs: [] } }),
  );
  await page.goto('/sweeps/9302');

  await page.getByRole('button', { name: 'Delete parameter sweep' }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Delete parameter sweep' }).click();
  await expect(page).toHaveURL(/\/sweeps$/);
  finishListRead();

  await expect(page.getByRole('main').getByText('No parameter sweeps', { exact: true })).toBeVisible();
  await expect(page).toHaveURL(/\/sweeps$/);
});

test('a list read from before the delete does not open the deleted backtest', async ({ page }) => {
  let socket: WebSocketRoute | undefined;
  let isListReadHeld = false;
  let finishListRead = (): void => undefined;
  const listRead = new Promise<void>((resolve) => {
    finishListRead = resolve;
  });
  await page.routeWebSocket(/\/ws\/backtests$/, (route) => {
    socket = route;
  });
  await page.route('**/api/backtests', async (route) => {
    if (isListReadHeld) {
      await listRead;
    }
    await route.fulfill({ json: [{ id: 9303, strategy_name: 'Fake', version_number: 1, status: 'finished', symbol: 'FAKE', metrics: null }] });
  });
  await page.route('**/api/backtests/9303', (route) =>
    route.request().method() === 'DELETE' ? route.fulfill({ status: 204 }) : route.fulfill({ status: 500, json: { detail: 'Detail read failed' } }),
  );
  await page.goto('/backtests/9303');

  const list = page.getByRole('complementary', { name: 'Backtests', exact: true });
  await list.getByRole('checkbox', { name: 'Select backtest #9303', exact: true }).check();
  await expect.poll(() => socket).toBeDefined();
  isListReadHeld = true;
  const heldListRead = page.waitForRequest('**/api/backtests');
  socket?.send(JSON.stringify({ type: 'changed' }));
  await heldListRead;
  await list.getByRole('button', { name: 'Delete', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Delete backtest', exact: true }).click();
  await expect(page).toHaveURL(/\/backtests$/);
  finishListRead();

  await expect(page.getByRole('main').getByText('No backtests', { exact: true })).toBeVisible();
  await expect(page).toHaveURL(/\/backtests$/);
});
