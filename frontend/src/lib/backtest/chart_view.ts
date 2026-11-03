// The "Equity" / "Bars" switcher of the backtest and forward test panels (docs/architecture/indicator.md section
// 23.9.8). The page address keeps the choice: ?chart=bars. "Equity" is the default and has no parameter.
export type ChartView = 'equity' | 'bars';

const CHART_PARAMETER = 'chart';

export const CHART_VIEW_ITEMS: readonly { value: ChartView; label: string }[] = [
  { value: 'equity', label: 'Equity' },
  { value: 'bars', label: 'Bars' },
];

export function readChartView(searchParameters: Pick<URLSearchParams, 'get'>): ChartView {
  return searchParameters.get(CHART_PARAMETER) === 'bars' ? 'bars' : 'equity';
}

/** The search part of the page address ("?..." or "") for `view`, with the other search parameters. */
export function formatChartViewSearch(searchParameters: Pick<URLSearchParams, 'toString'>, view: ChartView): string {
  const changed = new URLSearchParams(searchParameters.toString());
  if (view === 'bars') {
    changed.set(CHART_PARAMETER, 'bars');
  } else {
    changed.delete(CHART_PARAMETER);
  }
  const search = changed.toString();
  return search === '' ? '' : `?${search}`;
}
