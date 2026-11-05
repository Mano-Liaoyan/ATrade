<!-- The body of the results panel of the strategy workbench. A backtest tab shows the key metric row and the equity and
     drawdown chart of that backtest, or its status while it has no metrics. Trades, Orders, and Logs show the tables of
     the last selected backtest, like the backtest page: the API has no orders, and Logs shows the strategy error. The
     detail reads again when the status of the backtest changes, for example to finished.
     A failed or timed out backtest tab shows its error at once: the status with the last error line, the "Ask AI to fix"
     button (the AI assistant reads the error itself with read_backtest), and the full log.
     A backtest tab has the "Equity" / "Bars" switcher of the backtest page: "Bars" shows the bar chart of the backtest
     with the strategy indicators, "Add indicator", and the trade marks (docs/architecture/indicator.md section
     23.9.8). A multi-instrument backtest shows the universe member of the "Instrument" select. -->
<script lang="ts">
  import {
    BacktestTradeTable,
    ChartInstrumentSelect,
    ChartViewSwitcher,
    describeBacktestStatus,
    EquityDrawdownChart,
    findBacktestStatusKind,
    findErrorSummary,
    KeyMetricRow,
    listChartInstruments,
    readBacktest,
    readBacktestInstrument,
    type Backtest,
    type BacktestDetail,
    type BacktestInstrument,
    type ChartView,
  } from '#lib/backtest';
  import { Button, InlineNotification, StatusIndicator } from '#lib/foundation/carbon';
  import { EmptyText } from '#lib/foundation/empty_text';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { formatInstrument, RunAddIndicatorButton, RunBarChart, RunChart } from '#lib/market_data';
  import type { ResultTab } from './strategy_workbench';

  interface Props {
    /** The backtest of the tab, or of Trades, Orders, and Logs. Null when the strategy has no backtest. */
    backtest: Backtest | null;
    tab: ResultTab;
    /** The text without a backtest: "No backtests", or "No open backtests" when all backtest tabs are closed. */
    emptyText: string;
    /** Sends the error of a failed backtest to the AI assistant. */
    onAskAssistant: (backtestId: number) => void;
  }

  const { backtest, tab, emptyText, onAskAssistant }: Props = $props();

  let detail = $state<BacktestDetail | null>(null);
  let detailMessage = $state('');

  // Plain values, so the polled list (new objects each time) does not read the same detail again.
  const backtestId = $derived(backtest?.id ?? null);
  const backtestStatus = $derived(backtest?.status ?? null);
  const shownDetail = $derived(detail !== null && detail.id === backtest?.id ? detail : null);

  // Not in the page address: the strategy page keeps its own address (StrategyWorkbench).
  let chartView: ChartView = $state('equity');
  const runChart = new RunChart();
  $effect(() => {
    runChart.load(fetch);
  });

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
  <EmptyText text={emptyText} />
{:else if detailMessage !== ''}
  <InlineNotification kind="error" title="Backtest not read" subtitle={detailMessage} lowContrast />
{:else if shownDetail !== null}
  {@const run = shownDetail}
  {#if tab === 'trades'}
    <BacktestTradeTable trades={run.trades} />
  {:else if tab === 'orders'}
    <EmptyText text="No orders" />
  {:else if tab === 'logs'}
    {#if run.error_message === null}
      <EmptyText text="No logs" />
    {:else}
      <ScrollRegion label="Logs" fill>
        <pre class="log-text">{run.error_message}</pre>
      </ScrollRegion>
    {/if}
  {:else}
    {@const isMultiInstrument = readBacktestInstrument(run) === undefined}
    {@const chartInstruments = listChartInstruments(run)}
    {@const instrument = runChart.findInstrument(String(run.id), chartInstruments)}
    {#if instrument !== undefined}
      <div class="chart-tools">
        <ChartViewSwitcher
          value={chartView}
          onValueChange={(view: ChartView) => {
            chartView = view;
          }}
        />
        {#if chartView === 'bars'}
          {#if isMultiInstrument}
            <ChartInstrumentSelect
              instruments={chartInstruments}
              value={instrument}
              onValueChange={(selected: BacktestInstrument) => {
                runChart.selectInstrument(String(run.id), selected);
              }}
            />
          {/if}
          <RunAddIndicatorButton chart={runChart} runKey={String(run.id)} strategyIndicators={run.strategy_indicators} />
        {/if}
      </div>
    {/if}
    {#if chartView === 'bars' && instrument !== undefined}
      {#if run.metrics !== null}
        <KeyMetricRow metrics={run.metrics} startCapitalUsd={run.paper_capital_usd} />
      {/if}
      <div class="chart">
        <RunBarChart
          {instrument}
          isUniverseMember={isMultiInstrument}
          barPeriod={run.bar_period}
          range={{ startUtc: run.start_utc, endUtc: run.end_utc, sourceOrder: run.source_order }}
          label="Bar chart of {formatInstrument(instrument)}, {run.bar_period} bars"
          chart={runChart}
          runKey={String(run.id)}
          strategyIndicators={run.strategy_indicators}
          records={run.trades}
        />
      </div>
    {:else if run.metrics === null && (run.status === 'failed' || run.status === 'timed_out')}
      <div class="failure">
        <InlineNotification
          kind={run.status === 'failed' ? 'error' : 'warning'}
          title={describeBacktestStatus(run.status)}
          subtitle={findErrorSummary(run.error_message)}
          lowContrast
        />
        {#if run.status === 'failed' && run.error_message !== null && run.error_message !== ''}
          <div class="failure-actions">
            <Button
              size="sm"
              onclick={() => {
                onAskAssistant(run.id);
              }}>Ask AI to fix</Button
            >
          </div>
          <div class="failure-log">
            <ScrollRegion label="Log" fill>
              <pre class="log-text">{run.error_message}</pre>
            </ScrollRegion>
          </div>
        {/if}
      </div>
    {:else if run.metrics === null}
      <div class="state-area" role="status" aria-label="Backtest status">
        <StatusIndicator label={describeBacktestStatus(run.status)} kind={findBacktestStatusKind(run.status)} />
      </div>
    {:else}
      <KeyMetricRow metrics={run.metrics} startCapitalUsd={run.paper_capital_usd} />
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

  .chart-tools {
    display: flex;
    flex: none;
    gap: var(--cds-spacing-02);
    justify-content: flex-end;
    padding: var(--cds-spacing-03) var(--cds-spacing-05) 0;
  }

  .failure {
    display: flex;
    flex: 1;
    flex-direction: column;
    gap: var(--cds-spacing-05);
    min-block-size: 0;
    padding: var(--cds-spacing-05);
  }

  .failure :global(.cds--inline-notification) {
    flex: none;
    max-inline-size: none;
    margin: 0;
  }

  .failure-actions {
    display: flex;
    flex: none;
  }

  .failure-log {
    flex: 1;
    min-block-size: 0;
    border: 1px solid var(--cds-border-subtle-01);
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
