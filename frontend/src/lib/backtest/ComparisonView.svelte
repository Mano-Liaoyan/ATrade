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

  const METRIC_ROWS: { name: string; format: (metrics: BacktestMetrics) => string }[] = [
    { name: 'Final equity (USD)', format: (metrics) => formatUsd(metrics.final_equity_usd) },
    { name: 'Total return', format: (metrics) => formatPercent(metrics.total_return_percent) },
    { name: 'Max drawdown', format: (metrics) => formatPercent(metrics.max_drawdown_percent) },
    { name: 'Trades', format: (metrics) => String(metrics.trade_count) },
  ];
  const NO_METRICS = 'No result';

  function formatMetric(run: ComparedRun, format: (metrics: BacktestMetrics) => string): string {
    return run.metrics === null ? NO_METRICS : format(run.metrics);
  }
</script>

<section class="comparison" aria-label="Comparison">
  {#if code !== undefined}
    <h2>Code difference</h2>
    <CodeDiff firstCode={code.firstCode} secondCode={code.secondCode} firstLabel={first.label} secondLabel={second.label} />
  {/if}

  <h2>Metrics</h2>
  <ScrollRegion label="Compared metrics" maxHeight="18rem">
    <table class="metric-table">
      <thead>
        <tr>
          <th scope="col">Metric</th>
          <th scope="col">{first.label}</th>
          <th scope="col">{second.label}</th>
        </tr>
      </thead>
      <tbody>
        {#each METRIC_ROWS as row (row.name)}
          <tr>
            <th scope="row">{row.name}</th>
            <td class="number">{formatMetric(first, row.format)}</td>
            <td class="number">{formatMetric(second, row.format)}</td>
          </tr>
        {/each}
      </tbody>
    </table>
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
    gap: 0.75rem;
  }

  h2 {
    margin: 0;
    font-size: 1.125rem;
  }

  .metric-table {
    border-collapse: collapse;
    inline-size: 100%;
    font-size: 0.875rem;
  }

  .metric-table th,
  .metric-table td {
    padding: 0.375rem 0.75rem;
    border-bottom: 1px solid var(--color-border);
    text-align: start;
  }

  .metric-table thead th {
    position: sticky;
    inset-block-start: 0;
    background: var(--color-surface);
  }

  .metric-table .number {
    text-align: end;
    font-variant-numeric: tabular-nums;
  }
</style>
