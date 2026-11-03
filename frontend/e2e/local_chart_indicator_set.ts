// The chart indicator set (docs/architecture/indicator.md section 23.9.7) is one global row. The Playwright projects
// run at the same time against one database, and other specs open instrument pages too. So a chart test replaces
// GET and PUT /api/market-data/chart-indicators with a set in the browser context: it stays across page loads of the
// test and is not seen by other tests. backend/tests/market_data/test_chart_indicator_set_route.py tests the route.
import type { BrowserContext } from '@playwright/test';

export interface LocalChartIndicatorSet {
  /** The last saved set. */
  read: () => unknown;
}

export async function useLocalChartIndicatorSet(context: BrowserContext): Promise<LocalChartIndicatorSet> {
  let chartSet: unknown = { panes: [{ indicators: [] }], favorites: [] };
  await context.route('**/api/market-data/chart-indicators', async (route) => {
    if (route.request().method() === 'PUT') {
      chartSet = route.request().postDataJSON();
    }
    await route.fulfill({ json: chartSet });
  });
  return { read: () => chartSet };
}
