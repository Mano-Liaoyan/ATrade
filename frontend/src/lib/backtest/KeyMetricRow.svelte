<!-- The key metric row of a backtest or a forward test: the metrics of readKeyMetrics as MetricTiles in a MetricRow
     named "Metrics". The backtest page, the strategy page, and the forward test page all use it (spec #99). -->
<script lang="ts">
  import { MetricRow, MetricTile } from '#lib/foundation/metric_tile';
  import { readKeyMetrics, type KeyMetricInput } from './key_metrics';

  const { metrics, startCapitalUsd, trades }: KeyMetricInput = $props();

  const tiles = $derived(readKeyMetrics({ metrics, startCapitalUsd, trades }));
</script>

<MetricRow label="Metrics">
  {#each tiles as tile (tile.name)}
    <MetricTile {...tile} />
  {/each}
</MetricRow>
