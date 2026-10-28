<!-- The key metrics of 2 compared tests (backtests or a forward test and a backtest), one KeyMetricRow for each test, so
     the same metrics stand in the same columns (spec #99). The name of each test starts its line: a link to the test
     with the line style of its curve in the equity and drawdown chart (readCurveStyle). The region is
     "Compared metrics"; each row is "Metrics of <name>". -->
<script lang="ts">
  import { LineStyle } from 'lightweight-charts';
  import { readCurveStyle } from './chart_series';
  import type { ComparedTest } from './key_metrics';
  import KeyMetricRow from './KeyMetricRow.svelte';

  const { tests }: { tests: readonly ComparedTest[] } = $props();
</script>

<section class="compared-metrics" aria-label="Compared metrics">
  {#each tests as test, testIndex (test.href)}
    <div class="cds--tile test-name">
      <span
        class="curve-line"
        class:dashed={readCurveStyle(testIndex).lineStyle === LineStyle.Dashed}
        style:border-color={`var(${readCurveStyle(testIndex).colorVariable})`}
        aria-hidden="true"
      ></span>
      <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- the page resolves the path. -->
      <a class="cds--link" href={test.href} title={test.name}>{test.name}</a>
    </div>
    <KeyMetricRow
      label={`Metrics of ${test.name}`}
      metrics={test.metrics}
      startCapitalUsd={test.startCapitalUsd}
      trades={test.trades}
      period={test.period}
    />
  {/each}
</section>

<style>
  /* The name column has one width for both lines, so the tiles of both rows stand in the same columns. */
  .compared-metrics {
    display: grid;
    flex: none;
    grid-template-columns: minmax(0, 16rem) minmax(0, 1fr);
    background: var(--cds-border-subtle-01);
    column-gap: 1px;
  }

  .test-name {
    display: flex;
    align-items: center;
    gap: var(--cds-spacing-03);
    min-block-size: 0;
    min-inline-size: 0;
    padding: var(--cds-spacing-03) var(--cds-spacing-05);
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
    inline-size: var(--cds-spacing-06);
    border-top: 2px solid;
  }

  .curve-line.dashed {
    border-top-style: dashed;
  }
</style>
