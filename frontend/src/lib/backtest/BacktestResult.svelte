<!-- Result of one backtest: its status, the strategy error of a failed backtest, the metrics, the equity curve,
     and the trades. The metrics are Carbon tiles. The trade table scrolls inside its own region. -->
<script lang="ts">
  import { DataTable, StatusIndicator, type TableColumn } from '#lib/foundation/carbon';
  import { formatUtcTime } from '#lib/foundation/time_format';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import type { BacktestDetail, BacktestMetrics } from './backtest_api';
  import { describeBacktestStatus, findBacktestStatusKind, formatPercent, formatUsd } from './backtest_format';
  import EquityChart from './EquityChart.svelte';

  const { backtest }: { backtest: BacktestDetail } = $props();

  const METRICS: { name: string; format: (metrics: BacktestMetrics) => string }[] = [
    { name: 'Final equity (USD)', format: (metrics) => formatUsd(metrics.final_equity_usd) },
    { name: 'Total return', format: (metrics) => formatPercent(metrics.total_return_percent) },
    { name: 'Max drawdown', format: (metrics) => formatPercent(metrics.max_drawdown_percent) },
    { name: 'Trades', format: (metrics) => String(metrics.trade_count) },
  ];
  const TRADE_COLUMNS: TableColumn[] = [
    { header: 'Number', align: 'right' },
    { header: 'Time' },
    { header: 'Side' },
    { header: 'Quantity', align: 'right' },
    { header: 'Price (USD)', align: 'right' },
    { header: 'Commission (USD)', align: 'right' },
  ];
</script>

<section class="backtest-result" aria-label="Backtest result">
  <p role="status" aria-label="Backtest status">
    <StatusIndicator label={describeBacktestStatus(backtest.status)} kind={findBacktestStatusKind(backtest.status)} />
  </p>

  {#if backtest.status === 'failed' && backtest.error_message !== null}
    <h2>Strategy error</h2>
    <ScrollRegion label="Strategy error" maxHeight="24rem">
      <pre class="error-message">{backtest.error_message}</pre>
    </ScrollRegion>
  {/if}

  {#if backtest.metrics !== null}
    {@const metrics = backtest.metrics}
    <h2>Metrics</h2>
    <dl class="metrics atrade-auto-grid" aria-label="Metrics">
      {#each METRICS as metric (metric.name)}
        <div class="cds--tile metric">
          <dt>{metric.name}</dt>
          <dd>{metric.format(metrics)}</dd>
        </div>
      {/each}
    </dl>

    <h2>Equity curve</h2>
    <EquityChart curves={[{ name: 'Equity', points: backtest.equity_curve }]} label="Equity curve" />

    <h2>Trades</h2>
    {#if backtest.trades.length === 0}
      <p>The strategy made no trade.</p>
    {:else}
      <ScrollRegion label="Trades" maxHeight="18rem">
        <DataTable columns={TRADE_COLUMNS} size="sm">
          {#snippet rows()}
            {#each backtest.trades as trade, tradeIndex (tradeIndex)}
              <tr>
                <th scope="row" align="right">{tradeIndex + 1}</th>
                <td>{formatUtcTime(trade.time_utc)}</td>
                <td>{trade.side}</td>
                <td align="right">{trade.quantity_shares}</td>
                <td align="right">{formatUsd(trade.price_usd)}</td>
                <td align="right">{formatUsd(trade.commission_usd)}</td>
              </tr>
            {/each}
          {/snippet}
        </DataTable>
      </ScrollRegion>
    {/if}
  {/if}
</section>

<style>
  .backtest-result {
    display: flex;
    flex-direction: column;
    gap: var(--cds-spacing-05);
  }

  h2,
  p {
    margin: 0;
  }

  h2 {
    font-size: var(--cds-heading-03-font-size);
    font-weight: var(--cds-heading-03-font-weight);
    line-height: var(--cds-heading-03-line-height);
    letter-spacing: var(--cds-heading-03-letter-spacing);
  }

  .error-message {
    margin: 0;
    padding: var(--cds-spacing-05);
    background: var(--cds-layer-01);
    color: var(--cds-text-error);
    font-family: var(--cds-code-01-font-family);
    font-size: var(--cds-code-01-font-size);
    line-height: var(--cds-code-01-line-height);
    white-space: pre-wrap;
  }

  .metrics {
    gap: var(--cds-spacing-01);
    margin: 0;
  }

  .metric dt {
    font-size: var(--cds-label-01-font-size);
    line-height: var(--cds-label-01-line-height);
    letter-spacing: var(--cds-label-01-letter-spacing);
    color: var(--cds-text-secondary);
  }

  .metric dd {
    margin: var(--cds-spacing-03) 0 0;
    font-size: var(--cds-heading-04-font-size);
    font-weight: var(--cds-heading-04-font-weight);
    line-height: var(--cds-heading-04-line-height);
    font-variant-numeric: tabular-nums;
    text-align: end;
  }
</style>
