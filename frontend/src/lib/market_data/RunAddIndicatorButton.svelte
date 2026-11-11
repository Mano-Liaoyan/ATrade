<!-- "Add indicator" of a backtest or forward test bar chart (docs/architecture/indicator.md section 23.9.8): it adds to
     the run panes of `chart` (saved in the chart indicator set) and stars the favorite indicators of the saved chart indicator set. -->
<script lang="ts">
  import AddIndicatorButton from './AddIndicatorButton.svelte';
  import type { ChartIndicatorDefinition } from './chart_indicators';
  import type { RunChart } from './run_chart.svelte';
  import type { StrategyIndicator } from './strategy_indicators';

  interface Props {
    chart: RunChart;
    /** The run id. */
    runKey: string;
    strategyIndicators: readonly StrategyIndicator[];
  }

  const { chart, runKey, strategyIndicators }: Props = $props();
</script>

<AddIndicatorButton
  catalog={chart.indicators.catalog}
  favorites={chart.indicatorSet.favorites}
  onToggleFavorite={(key: string) => {
    chart.indicatorSet.toggleFavorite(fetch, key);
  }}
  onAdd={(definition: ChartIndicatorDefinition) => {
    chart.indicators.add(fetch, runKey, strategyIndicators, definition);
  }}
/>
