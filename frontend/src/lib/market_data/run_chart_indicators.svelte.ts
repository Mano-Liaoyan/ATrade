// The indicators of a backtest or forward test bar chart (docs/architecture/indicator.md section 23.9.8). The chart
// shows the panes of the saved chart indicator set and the strategy indicators. The user can add, change, and remove
// indicators. A change saves the panes without the strategy indicators in the set, so all charts get it. The changes
// of the strategy indicators are not saved and belong to one run (the key).
import type { ChartIndicatorSetStore } from './chart_indicator_set_store.svelte';
import { addChartIndicator, removeStrategyIndicators, type ChartIndicatorDefinition, type ChartPane } from './chart_indicators';
import { listChartIndicatorCatalog } from './indicator_series';
import { placeStrategyIndicators, type StrategyIndicator } from './strategy_indicators';

export class RunChartIndicators {
  catalog: ChartIndicatorDefinition[] = $state([]);
  #changed: { key: string; panes: ChartPane[] } | null = $state(null);
  // Not state: the last placed strategy indicators. The page reads a run again and again; the same panes object then
  // keeps the chart from drawing and reading the series again.
  #placed: { key: string; catalog: ChartIndicatorDefinition[]; savedPanes: ChartPane[]; panes: ChartPane[] } | null = null;
  readonly #indicatorSet: ChartIndicatorSetStore;

  constructor(indicatorSet: ChartIndicatorSetStore) {
    this.#indicatorSet = indicatorSet;
  }

  /** Reads the catalog. Call it in an effect. */
  loadCatalog(fetchFunction: typeof fetch): void {
    void listChartIndicatorCatalog(fetchFunction).then((result) => {
      if (result.kind === 'ok') {
        this.catalog = result.value;
      }
    });
  }

  readPanes(key: string, strategyIndicators: readonly StrategyIndicator[]): ChartPane[] {
    if (this.#changed?.key === key) {
      return this.#changed.panes;
    }
    const placedKey = `${key} ${JSON.stringify(strategyIndicators)}`;
    const savedPanes = this.#indicatorSet.panes;
    if (this.#placed?.key !== placedKey || this.#placed.catalog !== this.catalog || this.#placed.savedPanes !== savedPanes) {
      const panes = placeStrategyIndicators(strategyIndicators, this.catalog, savedPanes);
      this.#placed = { key: placedKey, catalog: this.catalog, savedPanes, panes };
    }
    return this.#placed.panes;
  }

  /** Shows the panes on the run `key` at once and saves them, without the strategy indicators, in the set. */
  changePanes(fetchFunction: typeof fetch, key: string, panes: ChartPane[]): void {
    this.#changed = { key, panes };
    this.#indicatorSet.changePanes(fetchFunction, removeStrategyIndicators(panes));
  }

  add(fetchFunction: typeof fetch, key: string, strategyIndicators: readonly StrategyIndicator[], definition: ChartIndicatorDefinition): void {
    this.changePanes(fetchFunction, key, addChartIndicator(this.readPanes(key, strategyIndicators), definition));
  }
}
