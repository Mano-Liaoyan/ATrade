// The indicators of a backtest or forward test bar chart (docs/architecture/indicator.md section 23.9.8). The chart
// starts with the strategy indicators. The user can add, change, and remove indicators; the changes are not saved and
// belong to one run (the key): another run starts again with its strategy indicators.
import { addChartIndicator, type ChartIndicatorDefinition, type ChartPane } from './chart_indicators';
import { listChartIndicatorCatalog } from './indicator_series';
import { placeStrategyIndicators, type StrategyIndicator } from './strategy_indicators';

export class RunChartIndicators {
  catalog: ChartIndicatorDefinition[] = $state([]);
  #changed: { key: string; panes: ChartPane[] } | null = $state(null);
  // Not state: the last placed strategy indicators. The page reads a run again and again; the same panes object then
  // keeps the chart from drawing and reading the series again.
  #placed: { key: string; catalog: ChartIndicatorDefinition[]; panes: ChartPane[] } | null = null;

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
    if (this.#placed?.key !== placedKey || this.#placed.catalog !== this.catalog) {
      this.#placed = { key: placedKey, catalog: this.catalog, panes: placeStrategyIndicators(strategyIndicators, this.catalog) };
    }
    return this.#placed.panes;
  }

  changePanes(key: string, panes: ChartPane[]): void {
    this.#changed = { key, panes };
  }

  add(key: string, strategyIndicators: readonly StrategyIndicator[], definition: ChartIndicatorDefinition): void {
    this.changePanes(key, addChartIndicator(this.readPanes(key, strategyIndicators), definition));
  }
}
