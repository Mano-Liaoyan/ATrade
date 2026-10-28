<!-- The body of the results panel of the strategy workbench. A backtest tab shows the key metric row and the equity and
     drawdown chart of that backtest, or its status while it has no metrics. Trades, Orders, and Logs show the tables of
     the last selected backtest, like the backtest page: the API has no orders, and Logs shows the strategy error. The
     detail reads again when the status of the backtest changes, for example to finished. -->
<script lang="ts">
  import {
    BacktestTradeTable,
    describeBacktestStatus,
    EquityDrawdownChart,
    findBacktestStatusKind,
    KeyMetricRow,
    readBacktest,
    type Backtest,
    type BacktestDetail,
  } from '#lib/backtest';
  import { InlineNotification, StatusIndicator } from '#lib/foundation/carbon';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import type { ResultTab } from './strategy_workbench';

  interface Props {
    /** The backtest of the tab, or of Trades, Orders, and Logs. Null when the strategy has no backtest. */
    backtest: Backtest | null;
    tab: ResultTab;
  }

  const { backtest, tab }: Props = $props();

  let detail = $state<BacktestDetail | null>(null);
  let detailMessage = $state('');

  // Plain values, so the polled list (new objects each time) does not read the same detail again.
  const backtestId = $derived(backtest?.id ?? null);
  const backtestStatus = $derived(backtest?.status ?? null);
  const shownDetail = $derived(detail !== null && detail.id === backtest?.id ? detail : null);

  $effect(() => {
    const id = backtestId;
    // A new status (for example finished) reads the detail again.
    if (id === null || backtestStatus === null) {
      return;
    }
    let isActive = true;
    void readBacktest(fetch, id).then((result) => {
      if (!isActive) {
        return;
      }
      if (result.kind === 'failed') {
        detailMessage = result.message;
        return;
      }
      detailMessage = '';
      detail = result.value;
    });
    return () => {
      isActive = false;
    };
  });
</script>

{#if backtest === null}
  <p class="empty-word">No backtests</p>
{:else if detailMessage !== ''}
  <InlineNotification kind="error" title="Backtest not read" subtitle={detailMessage} lowContrast />
{:else if shownDetail !== null}
  {@const run = shownDetail}
  {#if tab === 'trades'}
    <BacktestTradeTable trades={run.trades} />
  {:else if tab === 'orders'}
    <p class="empty-word">No orders</p>
  {:else if tab === 'logs'}
    {#if run.error_message === null}
      <p class="empty-word">No logs</p>
    {:else}
      <ScrollRegion label="Logs" fill>
        <pre class="log-text">{run.error_message}</pre>
      </ScrollRegion>
    {/if}
  {:else if run.metrics === null}
    <div class="state-area" role="status" aria-label="Backtest status">
      <StatusIndicator label={describeBacktestStatus(run.status)} kind={findBacktestStatusKind(run.status)} />
    </div>
  {:else}
    <KeyMetricRow metrics={run.metrics} startCapitalUsd={run.paper_capital_usd} trades={run.trades} />
    <div class="chart">
      {#key run.id}
        <EquityDrawdownChart
          curves={[{ name: 'Equity', points: run.equity_curve, startCapitalUsd: run.paper_capital_usd }]}
          label="Equity and drawdown"
          fill
        />
      {/key}
    </div>
  {/if}
{/if}

<style>
  .state-area {
    display: flex;
    flex: 1;
    align-items: center;
    justify-content: center;
    font-size: var(--cds-heading-compact-02-font-size);
    line-height: var(--cds-heading-compact-02-line-height);
  }

  /* The chart fills the rest of the panel body and follows its size (EquityDrawdownChart fill). */
  .chart {
    position: relative;
    flex: 1;
    min-block-size: 0;
    padding: var(--cds-spacing-03) var(--cds-spacing-05);
  }

  .empty-word {
    margin: 0;
    padding: var(--cds-spacing-05);
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
    color: var(--cds-text-secondary);
  }

  .log-text {
    margin: 0;
    padding: var(--cds-spacing-05);
    color: var(--cds-text-error);
    font-family: var(--cds-code-01-font-family);
    font-size: var(--cds-code-01-font-size);
    line-height: var(--cds-code-01-line-height);
    white-space: pre-wrap;
  }
</style>
