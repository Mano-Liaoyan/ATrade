<!-- The key metrics of 2 compared tests (backtests or a forward test and a backtest), one KeyMetricRow for each test, so
     the same metrics stand in the same columns with the full width of the backtest page row (spec #99). A line with the
     name of the test is above its row: a link to the test with the line style of its curve in the equity and drawdown
     chart (readCurveStyle). This line is the only key of the curves: the chart has no legend.
     The rows are in a ScrollRegion "Compared metrics" that fills its parent: in a low panel, the rows scroll with a
     visible track, so all metrics stay reachable. Each row is "Metrics of <name>". -->
<script lang="ts">
  import { LineStyle } from 'lightweight-charts';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { readCurveStyle } from './chart_series';
  import type { ComparedTest } from './key_metrics';
  import KeyMetricRow from './KeyMetricRow.svelte';

  const { tests }: { tests: readonly ComparedTest[] } = $props();
</script>

<ScrollRegion label="Compared metrics" fill>
  {#each tests as test, testIndex (test.href)}
    <div class="test-name">
      <span
        class="curve-line"
        class:dashed={readCurveStyle(testIndex).lineStyle === LineStyle.Dashed}
        style:border-color={`var(${readCurveStyle(testIndex).colorVariable})`}
        aria-hidden="true"
      ></span>
      <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- the page resolves the path. -->
      <a class="cds--link" href={test.href} title={test.name}>{test.name}</a>
    </div>
    <KeyMetricRow label={`Metrics of ${test.name}`} metrics={test.metrics} startCapitalUsd={test.startCapitalUsd} />
  {/each}
</ScrollRegion>

<style>
  .test-name {
    display: flex;
    align-items: center;
    gap: var(--cds-spacing-03);
    min-inline-size: 0;
    padding: var(--cds-spacing-02) var(--cds-spacing-05);
    background: var(--cds-layer-01);
    border-block-end: 1px solid var(--cds-border-subtle-01);
  }

  .test-name a {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
  }

  .curve-line {
    flex: none;
    inline-size: var(--cds-spacing-07);
    border-top: 2px solid;
  }

  .curve-line.dashed {
    border-top-style: dashed;
  }
</style>
