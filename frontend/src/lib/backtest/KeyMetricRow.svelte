<!-- The key metric row of a backtest or a forward test: the metrics of readKeyMetrics as MetricTiles in a MetricRow
     named `label` ("Metrics" by default). It is for the backtest page, the strategy page, the forward test page, and
     the comparison pages, which show one row for each compared test (spec #99). -->
<script lang="ts">
  import { MetricRow, MetricTile } from '#lib/foundation/metric_tile';
  import { readKeyMetrics, type KeyMetricInput } from './key_metrics';

  interface Props extends KeyMetricInput {
    label?: string;
  }

  const { metrics, startCapitalUsd, label = 'Metrics' }: Props = $props();

  const tiles = $derived(readKeyMetrics({ metrics, startCapitalUsd }));
</script>

<MetricRow {label}>
  {#each tiles as tile (tile.name)}
    <MetricTile {...tile} />
  {/each}
</MetricRow>
