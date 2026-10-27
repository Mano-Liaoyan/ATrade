<!-- Comparison of two runs of the same strategy (docs/architecture section 9.5): the code diff, the metric table,
     and both equity curves on one chart. A run is a backtest or a forward test, so the view takes only labels,
     metrics, and equity curves. The code diff is optional: two runs of the same strategy version have no diff
     (forward test comparison, section 12.10). The metric table scrolls inside its own region. -->
<script module lang="ts">
  import type { BacktestMetrics, EquityPoint } from './backtest_api';

  export interface ComparedRun {
    label: string;
    metrics: BacktestMetrics | null;
    equityCurve: EquityPoint[];
  }

  export interface ComparedCode {
    firstCode: string;
    secondCode: string;
  }
</script>

<script lang="ts">
  import { Button, DataTable, InlineNotification, type TableColumn } from '#lib/foundation/carbon';
  import { CodeDiff } from '#lib/foundation/code_editor';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { formatPercent, formatUsd } from './backtest_format';
  import EquityChart from './EquityChart.svelte';
  import type { TimeInterval } from './interruption_marks';

  interface Props {
    first: ComparedRun;
    second: ComparedRun;
    code?: ComparedCode | undefined;
    // Interruptions of a forward test, marked grey on the equity chart (section 12.10).
    interruptions?: TimeInterval[];
  }

  const { first, second, code, interruptions = [] }: Props = $props();

  let isSameCodeOpen = $state(false);

  const METRIC_ROWS: { name: string; format: (metrics: BacktestMetrics) => string }[] = [
    { name: 'Final equity (USD)', format: (metrics) => formatUsd(metrics.final_equity_usd) },
    { name: 'Total return', format: (metrics) => formatPercent(metrics.total_return_percent) },
    { name: 'Max drawdown', format: (metrics) => formatPercent(metrics.max_drawdown_percent) },
    { name: 'Trades', format: (metrics) => String(metrics.trade_count) },
  ];
  const NO_METRICS = 'No result';
  const metricColumns: TableColumn[] = $derived([
    { header: 'Metric' },
    { header: first.label, align: 'right' },
    { header: second.label, align: 'right' },
  ]);

  function formatMetric(run: ComparedRun, format: (metrics: BacktestMetrics) => string): string {
    return run.metrics === null ? NO_METRICS : format(run.metrics);
  }
</script>

<section class="comparison" aria-label="Comparison">
  {#if code !== undefined}
    <h2>Code difference</h2>
    {#if code.firstCode === code.secondCode}
      <!-- Saving the same code again keeps the version, so the same code means the same strategy version. -->
      <InlineNotification kind="info" label="Code difference" title="Same strategy version: no code difference." lowContrast />
      <div>
        <Button
          kind="ghost"
          size="sm"
          aria-expanded={isSameCodeOpen}
          onclick={() => {
            isSameCodeOpen = !isSameCodeOpen;
          }}
        >
          {isSameCodeOpen ? 'Hide the code' : 'Show the code'}
        </Button>
      </div>
      {#if isSameCodeOpen}
        <CodeDiff
          firstCode={code.firstCode}
          secondCode={code.secondCode}
          firstLabel={first.label}
          secondLabel={second.label}
          collapseUnchanged={false}
        />
      {/if}
    {:else}
      <CodeDiff firstCode={code.firstCode} secondCode={code.secondCode} firstLabel={first.label} secondLabel={second.label} />
    {/if}
  {/if}

  <h2>Metrics</h2>
  <ScrollRegion label="Compared metrics" maxHeight="18rem">
    <DataTable columns={metricColumns} size="sm">
      {#snippet rows()}
        {#each METRIC_ROWS as row (row.name)}
          <tr>
            <th scope="row">{row.name}</th>
            <td align="right">{formatMetric(first, row.format)}</td>
            <td align="right">{formatMetric(second, row.format)}</td>
          </tr>
        {/each}
      {/snippet}
    </DataTable>
  </ScrollRegion>

  <h2>Equity curves</h2>
  <EquityChart
    curves={[
      { name: first.label, points: first.equityCurve },
      { name: second.label, points: second.equityCurve },
    ]}
    label="Compared equity curves"
    {interruptions}
  />
</section>

<style>
  .comparison {
    display: flex;
    flex-direction: column;
    gap: var(--cds-spacing-05);
  }

  h2 {
    margin: 0;
    font-size: var(--cds-heading-03-font-size);
    font-weight: var(--cds-heading-03-font-weight);
    line-height: var(--cds-heading-03-line-height);
    letter-spacing: var(--cds-heading-03-letter-spacing);
  }
</style>
