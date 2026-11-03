// The strategy indicators of a backtest or forward test bar chart (docs/architecture/indicator.md section 23.9.8):
// `strategy_indicators` of the detail route, from CHART_INDICATORS of the strategy version code.
import type { components } from '#lib/api';
import { addChartIndicator, withDefaults, type ChartIndicatorDefinition, type ChartPane } from './chart_indicators';

export type StrategyIndicator = components['schemas']['ChartIndicator'];

/**
 * The panes of the strategy indicators: each indicator is added as a new indicator (section 23.9.3: placement and the
 * next free colors), with its parameters and the catalog defaults of the others. An indicator that is not in the
 * catalog is left out.
 */
export function placeStrategyIndicators(
  strategyIndicators: readonly StrategyIndicator[],
  catalog: readonly ChartIndicatorDefinition[],
): ChartPane[] {
  let panes: ChartPane[] = [{ indicators: [] }];
  for (const item of strategyIndicators) {
    const definition = catalog.find((entry) => entry.key === item.indicator);
    if (definition === undefined) {
      continue;
    }
    const parameters = withDefaults(definition, item.parameters);
    const oldIndicators = new Set(panes.flatMap((pane) => pane.indicators));
    // addChartIndicator gives the new indicator the catalog defaults; it is the only indicator that is not old.
    panes = addChartIndicator(panes, definition).map((pane) => ({
      indicators: pane.indicators.map((indicator) => (oldIndicators.has(indicator) ? indicator : { ...indicator, parameters })),
    }));
  }
  return panes;
}
