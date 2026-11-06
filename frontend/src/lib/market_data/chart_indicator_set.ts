// The chart indicator set (docs/architecture/indicator.md section 23.9.7): the indicators of the instrument page
// chart and the favorites of "Add indicator". Calls GET and PUT /api/market-data/chart-indicators. The last PUT wins.
import type { components } from '#lib/api';
import { BACKEND_NOT_REACHABLE, jsonRequest, readErrorMessage, readJsonBody, requestJson, sendRequest, type RequestResult } from '#lib/foundation/http_request';
import type { ChartIndicatorDefinition, ChartPane } from './chart_indicators';

/** The first pane is the price pane. `favorites` holds catalog keys. */
export interface ChartIndicatorSet {
  panes: ChartPane[];
  favorites: string[];
}

type IndicatorProblem = components['schemas']['IndicatorProblemResponse'];

const CHART_INDICATORS_PATH = '/api/market-data/chart-indicators';

/** The set of the migration: the price pane without indicators, and no favorites. */
export const EMPTY_CHART_INDICATOR_SET: ChartIndicatorSet = { panes: [{ indicators: [] }], favorites: [] };

/** The API type `ChartIndicatorSet` has `style: string`. The PUT route refuses other styles than the 3 of
 * `ChartLineStyle`, so the saved set has only these. */
export function readChartIndicatorSet(fetchFunction: typeof fetch): Promise<RequestResult<ChartIndicatorSet>> {
  return requestJson<ChartIndicatorSet>(fetchFunction, 'Reading the chart indicators', CHART_INDICATORS_PATH);
}

/** A refused set gives the message of its first problem. Another failure gives the `detail` text. */
export async function saveChartIndicatorSet(fetchFunction: typeof fetch, chartSet: ChartIndicatorSet): Promise<RequestResult<ChartIndicatorSet>> {
  const response = await sendRequest(fetchFunction, CHART_INDICATORS_PATH, jsonRequest('PUT', chartSet));
  if (response === null) {
    return { kind: 'failed', message: BACKEND_NOT_REACHABLE };
  }
  if (!response.ok) {
    const problems = ((await readJsonBody(response.clone())) as { problems?: IndicatorProblem[] } | null)?.problems;
    const firstProblem = Array.isArray(problems) ? problems[0] : undefined;
    return { kind: 'failed', message: firstProblem?.message ?? (await readErrorMessage(response, 'Saving the chart indicators')) };
  }
  return { kind: 'ok', value: (await response.json()) as ChartIndicatorSet };
}

/** A favorite key goes out of the list. Another key goes in at the end. */
export function toggleFavorite(favorites: readonly string[], key: string): string[] {
  return favorites.includes(key) ? favorites.filter((favorite) => favorite !== key) : [...favorites, key];
}

/** The favorites first, then the others, each in catalog order (section 23.9.5). */
export function orderByFavorites(catalog: readonly ChartIndicatorDefinition[], favorites: readonly string[]): ChartIndicatorDefinition[] {
  return [...catalog.filter((item) => favorites.includes(item.key)), ...catalog.filter((item) => !favorites.includes(item.key))];
}
