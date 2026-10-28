<!-- PROTOTYPE (#99), throwaway: the results pane of the strategy workbench. One tab for each backtest of the strategy,
     then Trades / Orders / Logs of the selected backtest. A backtest tab shows the metrics in one row and the equity
     curve with the drawdown below it. -->
<script lang="ts">
  import {
    describeBacktestStatus,
    findBacktestStatusKind,
    formatPercent,
    formatUsd,
    readBacktest,
    type Backtest,
    type BacktestDetail,
  } from '#lib/backtest';
  import { DataTable, StatusIndicator, Tabs, type TabItem, type TableColumn } from '#lib/foundation/carbon';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { formatUtcTime } from '#lib/foundation/time_format';
  import { formatBarPeriod } from '#lib/foundation/value_format';
  import { formatVersionLabel } from '#lib/strategy';
  import WorkbenchRunChart from './WorkbenchRunChart.svelte';
  import { backtestTab, type PanelSize, type ResultsTab } from './workbench_layout';
  import WorkbenchTabLine from './WorkbenchTabLine.svelte';

  interface Props {
    // The backtests of the strategy, the newest first.
    backtests: Backtest[];
    tab: ResultsTab;
    // The backtest that Trades, Orders, and Logs show.
    backtestId: number | null;
    size: PanelSize;
    isCollapsed: boolean;
    onTabChange: (tab: ResultsTab) => void;
    onToggleMinimized: () => void;
    onToggleMaximized: () => void;
  }

  const { backtests, tab, backtestId, size, isCollapsed, onTabChange, onToggleMinimized, onToggleMaximized }: Props =
    $props();

  const TRADE_COLUMNS: TableColumn[] = [
    { header: 'Time (UTC)' },
    { header: 'Side' },
    { header: 'Quantity', align: 'right' },
    { header: 'Price (USD)', align: 'right' },
    { header: 'Commission (USD)', align: 'right' },
  ];

  const tabItems: TabItem[] = $derived([
    ...backtests.map((backtest) => ({
      value: backtestTab(backtest.id),
      label:
        backtest.metrics === null
          ? `Backtest ${String(backtest.id)}`
          : `Backtest ${String(backtest.id)}  ${formatPercent(backtest.metrics.total_return_percent)}`,
    })),
    { value: 'trades', label: 'Trades' },
    { value: 'orders', label: 'Orders' },
    { value: 'logs', label: 'Logs' },
  ]);

  const backtest = $derived(backtests.find((candidate) => candidate.id === backtestId) ?? null);
  let detail = $state<BacktestDetail | null>(null);
  let detailError = $state('');

  // The detail is read again when the backtest changes or when its status changes (for example to finished).
  // A string, so the polled list (new objects each time) does not read the same detail again.
  const backtestKey = $derived(backtest === null ? '' : `${String(backtest.id)}:${backtest.status}`);
  $effect(() => {
    const id = Number(backtestKey.split(':')[0]);
    if (backtestKey === '') {
      detail = null;
      return;
    }
    void readBacktest(fetch, id).then((result) => {
      if (result.kind === 'failed') {
        detailError = result.message;
        return;
      }
      detailError = '';
      detail = result.value;
    });
  });

  const logLines = $derived.by(() => {
    if (detail === null) {
      return [];
    }
    const lines = [`${formatUtcTime(detail.created_at_utc)}  Queued`];
    if (detail.started_at_utc !== null) {
      lines.push(`${formatUtcTime(detail.started_at_utc)}  Started`);
    }
    if (detail.ended_at_utc !== null) {
      lines.push(`${formatUtcTime(detail.ended_at_utc)}  ${describeBacktestStatus(detail.status)}`);
    }
    if (detail.error_message !== null) {
      lines.push(detail.error_message);
    }
    return lines;
  });
</script>

<section class="results-pane" aria-label="Results">
  <WorkbenchTabLine {size} {onToggleMinimized} {onToggleMaximized}>
    <div class="result-tabs">
      <Tabs
        label="Results"
        items={tabItems}
        value={tab}
        onValueChange={(value: string) => {
          onTabChange(value as ResultsTab);
        }}
      />
    </div>
  </WorkbenchTabLine>

  {#if isCollapsed}
    <!-- Only the tab line shows. -->
  {:else if backtest === null || detail === null}
    <p class="pane-empty">{detailError !== '' ? detailError : backtests.length === 0 ? 'No backtest yet.' : ''}</p>
  {:else if tab.startsWith('backtest-')}
    <div class="metric-row">
      <div class="cds--tile metric">
        <span class="metric-name">Strategy version</span>
        <span class="metric-value">{formatVersionLabel(detail.strategy_name, detail.version_number)}</span>
      </div>
      <div class="cds--tile metric">
        <span class="metric-name">Instrument</span>
        <span class="metric-value">{detail.symbol} · {formatBarPeriod(detail.bar_period)}</span>
      </div>
      {#if detail.metrics === null}
        <div class="cds--tile metric">
          <span class="metric-name">Status</span>
          <span class="metric-value">
            <StatusIndicator label={describeBacktestStatus(detail.status)} kind={findBacktestStatusKind(detail.status)} />
          </span>
        </div>
      {:else}
        <div class="cds--tile metric number">
          <span class="metric-name">Final equity (USD)</span>
          <span class="metric-value">{formatUsd(detail.metrics.final_equity_usd)}</span>
        </div>
        <div class="cds--tile metric number">
          <span class="metric-name">Total return</span>
          <span class="metric-value">{formatPercent(detail.metrics.total_return_percent)}</span>
        </div>
        <div class="cds--tile metric number">
          <span class="metric-name">Max drawdown</span>
          <span class="metric-value">{formatPercent(detail.metrics.max_drawdown_percent)}</span>
        </div>
        <div class="cds--tile metric number">
          <span class="metric-name">Trades</span>
          <span class="metric-value">{detail.metrics.trade_count}</span>
        </div>
      {/if}
    </div>
    <div class="chart-area">
      {#key detail.id}
        <WorkbenchRunChart points={detail.equity_curve} label={`Backtest ${String(detail.id)} equity and drawdown`} />
      {/key}
    </div>
  {:else if tab === 'trades'}
    <div class="table-area">
      <ScrollRegion label="Trades" maxHeight="100%">
        <DataTable columns={TRADE_COLUMNS} size="sm">
          {#snippet rows()}
            {#each detail?.trades ?? [] as trade, index (index)}
              <tr>
                <td>{formatUtcTime(trade.time_utc)}</td>
                <td>{trade.side === 'BUY' ? 'Buy' : 'Sell'}</td>
                <td align="right">{trade.quantity_shares}</td>
                <td align="right">{formatUsd(trade.price_usd)}</td>
                <td align="right">{formatUsd(trade.commission_usd)}</td>
              </tr>
            {/each}
          {/snippet}
        </DataTable>
      </ScrollRegion>
    </div>
  {:else if tab === 'orders'}
    <p class="pane-empty">The backtest API returns trades only, not orders.</p>
  {:else}
    <div class="table-area">
      <ScrollRegion label="Logs" maxHeight="100%">
        <ol class="log-lines">
          {#each logLines as line, index (index)}
            <li>{line}</li>
          {/each}
        </ol>
      </ScrollRegion>
    </div>
  {/if}
</section>

<style>
  .results-pane {
    display: flex;
    flex-direction: column;
    block-size: 100%;
    min-block-size: 0;
  }

  .result-tabs {
    block-size: 100%;
  }

  .result-tabs :global(.cds--tabs__nav-item-label) {
    white-space: pre;
    font-variant-numeric: tabular-nums;
  }

  .pane-empty {
    margin: 0;
    padding: var(--cds-spacing-05);
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
    color: var(--cds-text-secondary);
  }

  .metric-row {
    display: grid;
    flex: none;
    grid-auto-columns: minmax(0, 1fr);
    grid-auto-flow: column;
    gap: 1px;
    border-block-end: 1px solid var(--cds-border-subtle-01);
    background: var(--cds-border-subtle-01);
  }

  .metric {
    display: flex;
    flex-direction: column;
    gap: var(--cds-spacing-02);
    min-block-size: 0;
    padding: var(--cds-spacing-03) var(--cds-spacing-05);
  }

  .metric.number {
    align-items: end;
  }

  .metric-name {
    font-size: var(--cds-label-01-font-size);
    line-height: var(--cds-label-01-line-height);
    letter-spacing: var(--cds-label-01-letter-spacing);
    color: var(--cds-text-secondary);
  }

  .metric-value {
    overflow: hidden;
    font-size: var(--cds-heading-compact-02-font-size);
    font-weight: var(--cds-heading-compact-02-font-weight);
    line-height: var(--cds-heading-compact-02-line-height);
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
    text-overflow: ellipsis;
  }

  .chart-area {
    flex: 1;
    min-block-size: 0;
  }

  .table-area {
    position: relative;
    flex: 1;
    min-block-size: 0;
  }

  .table-area :global(.scroll-region) {
    position: absolute;
    inset: 0;
  }

  .log-lines {
    margin: 0;
    padding: var(--cds-spacing-03) var(--cds-spacing-05);
    list-style: none;
    font-family: var(--cds-code-01-font-family, 'IBM Plex Mono', monospace);
    font-size: var(--cds-code-01-font-size);
    line-height: var(--cds-code-01-line-height);
  }
</style>
