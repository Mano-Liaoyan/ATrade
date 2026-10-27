<!-- Result of one backtest: its status, the strategy error of a failed backtest, the metrics, the equity curve,
     and the trades. The trade table scrolls inside its own region. -->
<script lang="ts">
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import type { BacktestDetail } from './backtest_api';
  import { describeBacktestStatus, formatPercent, formatUsd } from './backtest_format';
  import EquityChart from './EquityChart.svelte';

  const { backtest }: { backtest: BacktestDetail } = $props();
</script>

<section class="backtest-result" aria-label="Backtest result">
  <p class="status" role="status" aria-label="Backtest status">{describeBacktestStatus(backtest.status)}</p>

  {#if backtest.status === 'failed' && backtest.error_message !== null}
    <h2>Strategy error</h2>
    <ScrollRegion label="Strategy error" maxHeight="24rem">
      <pre class="error-message">{backtest.error_message}</pre>
    </ScrollRegion>
  {:else if backtest.status === 'timed_out'}
    <p>The backtest ran longer than the timeout. ATrade stopped it.</p>
  {/if}

  {#if backtest.metrics !== null}
    <h2>Metrics</h2>
    <dl class="metrics" aria-label="Metrics">
      <div>
        <dt>Final equity (USD)</dt>
        <dd>{formatUsd(backtest.metrics.final_equity_usd)}</dd>
      </div>
      <div>
        <dt>Total return</dt>
        <dd>{formatPercent(backtest.metrics.total_return_percent)}</dd>
      </div>
      <div>
        <dt>Max drawdown</dt>
        <dd>{formatPercent(backtest.metrics.max_drawdown_percent)}</dd>
      </div>
      <div>
        <dt>Trades</dt>
        <dd>{backtest.metrics.trade_count}</dd>
      </div>
    </dl>

    <h2>Equity curve</h2>
    <EquityChart curves={[{ name: "Equity", points: backtest.equity_curve }]} label="Equity curve" />

    <h2>Trades</h2>
    {#if backtest.trades.length === 0}
      <p>The strategy made no trade.</p>
    {:else}
      <ScrollRegion label="Trades" maxHeight="18rem">
        <table class="trades">
          <thead>
            <tr>
              <th scope="col">Number</th>
              <th scope="col">Time (UTC)</th>
              <th scope="col">Side</th>
              <th scope="col">Quantity</th>
              <th scope="col">Price (USD)</th>
              <th scope="col">Commission (USD)</th>
            </tr>
          </thead>
          <tbody>
            {#each backtest.trades as trade, tradeIndex (tradeIndex)}
              <tr>
                <th scope="row">{tradeIndex + 1}</th>
                <td>{trade.time_utc}</td>
                <td>{trade.side}</td>
                <td class="number">{trade.quantity_shares}</td>
                <td class="number">{formatUsd(trade.price_usd)}</td>
                <td class="number">{formatUsd(trade.commission_usd)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </ScrollRegion>
    {/if}
  {/if}
</section>

<style>
  .backtest-result {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  h2,
  p {
    margin: 0;
  }

  h2 {
    font-size: 1.125rem;
  }

  .status {
    font-weight: 600;
  }

  .error-message {
    margin: 0;
    padding: 0.75rem;
    border: 1px solid var(--color-border);
    border-radius: 0.5rem;
    background: var(--color-surface);
    color: var(--color-warning);
    font-size: 0.8125rem;
    white-space: pre-wrap;
  }

  .metrics {
    display: flex;
    flex-wrap: wrap;
    gap: 1.5rem;
    margin: 0;
  }

  .metrics dt {
    color: var(--color-muted);
    font-size: 0.875rem;
  }

  .metrics dd {
    margin: 0;
    font-size: 1.25rem;
    font-variant-numeric: tabular-nums;
  }

  .trades {
    border-collapse: collapse;
    inline-size: 100%;
    font-size: 0.875rem;
  }

  .trades th,
  .trades td {
    padding: 0.375rem 0.75rem;
    border-bottom: 1px solid var(--color-border);
    text-align: start;
  }

  .trades thead th {
    position: sticky;
    inset-block-start: 0;
    background: var(--color-surface);
  }

  .trades .number {
    text-align: end;
    font-variant-numeric: tabular-nums;
  }
</style>
