<!-- PROTOTYPE (#99), throwaway: the backtest workbench. Left: the backtest list (select 2 rows to compare). Main: one
     header line, one row of key metrics, the equity and drawdown curves on one time axis, a drag splitter, and the
     Trades / Orders / Logs tabs. The page does not scroll: the list and the tab tables scroll in their own regions.
     The API has no orders, no logs, and no Sharpe ratio. The win rate is computed here from the trades.
     Each panel (chart, tables) has minimize and maximize buttons at the end of its header line, like an IDE. -->
<script lang="ts">
  import Add16 from '@carbon/icons/es/add/16.js';
  import ConnectionSignal16 from '@carbon/icons/es/connection-signal/16.js';
  import Maximize16 from '@carbon/icons/es/maximize/16.js';
  import Minimize16 from '@carbon/icons/es/minimize/16.js';
  import Subtract16 from '@carbon/icons/es/subtract/16.js';
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import {
    checkComparisonSelection,
    describeBacktestStatus,
    findBacktestStatusKind,
    formatPercent,
    formatUsd,
    isFinalStatus,
    listBacktests,
    readBacktest,
    type Backtest,
    type BacktestDetail,
    type BacktestTrade,
  } from '#lib/backtest';
  import {
    Checkbox,
    DataTable,
    Icon,
    InlineNotification,
    StatusIndicator,
    Tabs,
    Tooltip,
    type TableColumn,
  } from '#lib/foundation/carbon';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { formatUtcTime } from '#lib/foundation/time_format';
  import { formatBarPeriod } from '#lib/foundation/value_format';
  import { isLiveBarPeriod, startForwardTest } from '#lib/forward_test';
  import { formatVersionLabel } from '#lib/strategy';
  import BacktestEquityDrawdownChart from './BacktestEquityDrawdownChart.svelte';

  const { backtestId }: { backtestId: number | null } = $props();

  const STATUS_CHECK_INTERVAL_MILLISECONDS = 1000;
  const LIST_CHECK_INTERVAL_MILLISECONDS = 2000;
  const PERCENT = 100;
  const MIN_PANEL_HEIGHT_PIXELS = 96;
  const MIN_CHART_HEIGHT_PIXELS = 160;
  const DEFAULT_PANEL_HEIGHT_PIXELS = 240;
  const KEYBOARD_STEP_PIXELS = 16;
  const COMPARED_BACKTEST_COUNT = 2;

  const LIST_COLUMNS: TableColumn[] = [
    { header: 'Select', isSelection: true },
    { header: '#', align: 'right' },
    { header: 'Strategy' },
    { header: 'Instrument' },
    { header: 'Status' },
    { header: 'Return', align: 'right' },
  ];
  const TRADE_COLUMNS: TableColumn[] = [
    { header: '#', align: 'right' },
    { header: 'Time' },
    { header: 'Side' },
    { header: 'Quantity', align: 'right' },
    { header: 'Price (USD)', align: 'right' },
    { header: 'Commission (USD)', align: 'right' },
  ];
  const TAB_ITEMS = [
    { value: 'trades', label: 'Trades' },
    { value: 'orders', label: 'Orders' },
    { value: 'logs', label: 'Logs' },
  ];

  let backtests: Backtest[] = $state([]);
  let listMessage = $state('');
  let checkedIds: number[] = $state([]);
  let backtest = $state<BacktestDetail | null>(null);
  let detailMessage = $state('');
  let selectedTab = $state('trades');
  let panelHeightPixels = $state(DEFAULT_PANEL_HEIGHT_PIXELS);
  let mainElement: HTMLDivElement | undefined = $state();
  let dragStart: { pointerYPixels: number; panelHeightPixels: number } | undefined;
  let forwardTestMessage = $state('');
  let isStartingForwardTest = $state(false);

  // The panel layout: both panels, one panel maximized (the other shows only its header line).
  // "Minimize chart" is the same layout as "maximize tables", and the other way round.
  type PanelLayout = 'split' | 'chart-max' | 'tables-max';
  type PanelName = 'chart' | 'tables';
  const PANEL_LAYOUT_STORAGE_KEY = 'atrade.prototype99.backtestPanelLayout';
  const PANEL_LAYOUTS: readonly PanelLayout[] = ['split', 'chart-max', 'tables-max'];

  function readStoredPanelLayout(): PanelLayout {
    try {
      const stored = localStorage.getItem(PANEL_LAYOUT_STORAGE_KEY);
      return PANEL_LAYOUTS.find((layout) => layout === stored) ?? 'split';
    } catch {
      return 'split';
    }
  }

  let panelLayout = $state<PanelLayout>(readStoredPanelLayout());

  $effect(() => {
    try {
      localStorage.setItem(PANEL_LAYOUT_STORAGE_KEY, panelLayout);
    } catch {
      // The layout is only not remembered.
    }
  });

  function maximizedLayout(panel: PanelName): PanelLayout {
    return panel === 'chart' ? 'chart-max' : 'tables-max';
  }

  function minimizedLayout(panel: PanelName): PanelLayout {
    return panel === 'chart' ? 'tables-max' : 'chart-max';
  }

  function toggleLayout(layout: PanelLayout): void {
    panelLayout = panelLayout === layout ? 'split' : layout;
  }

  function restoreWithEscape(event: KeyboardEvent): void {
    if (event.key === 'Escape' && panelLayout !== 'split' && !event.defaultPrevented) {
      panelLayout = 'split';
    }
  }

  // A double click on an empty part of a header line toggles maximize. Controls in the line keep their own action.
  function toggleMaximizeFromHeader(event: MouseEvent, panel: PanelName): void {
    if (event.target instanceof Element && event.target.closest('a, button, input, [role="tab"]') !== null) {
      return;
    }
    toggleLayout(maximizedLayout(panel));
  }

  const comparison = $derived(checkComparisonSelection(backtests, checkedIds));
  const showsBatchActions = $derived(checkedIds.length >= COMPARED_BACKTEST_COUNT);
  const shownBacktest = $derived(backtest !== null && backtest.id === backtestId ? backtest : null);

  // The list reads again while a backtest in it is queued or running.
  $effect(() => {
    let isActive = true;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function readList(): Promise<void> {
      const result = await listBacktests(fetch);
      if (!isActive) {
        return;
      }
      if (result.kind === 'failed') {
        listMessage = result.message;
        return;
      }
      listMessage = '';
      backtests = result.value;
      if (result.value.some((item) => !isFinalStatus(item.status))) {
        timer = setTimeout(() => void readList(), LIST_CHECK_INTERVAL_MILLISECONDS);
      }
    }

    void readList();
    return () => {
      isActive = false;
      clearTimeout(timer);
    };
  });

  // /backtests opens the newest backtest.
  $effect(() => {
    const newest = backtests.reduce<Backtest | undefined>(
      (found, item) => (found === undefined || item.id > found.id ? item : found),
      undefined,
    );
    if (backtestId === null && newest !== undefined) {
      void goto(resolve('/backtests/[backtestId]', { backtestId: String(newest.id) }), { replaceState: true });
    }
  });

  // The selected backtest reads again until its status is final.
  $effect(() => {
    if (backtestId === null) {
      return;
    }
    let isActive = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const id = backtestId;
    forwardTestMessage = '';

    async function readUntilFinal(): Promise<void> {
      const result = await readBacktest(fetch, id);
      if (!isActive) {
        return;
      }
      if (result.kind === 'failed') {
        detailMessage = result.message;
      } else {
        detailMessage = '';
        backtest = result.value;
        if (isFinalStatus(result.value.status)) {
          return;
        }
      }
      timer = setTimeout(() => void readUntilFinal(), STATUS_CHECK_INTERVAL_MILLISECONDS);
    }

    void readUntilFinal();
    return () => {
      isActive = false;
      clearTimeout(timer);
    };
  });

  function instrumentHref(item: Backtest): string {
    const path = resolve('/instruments/[exchange]/[symbol]', { exchange: item.exchange, symbol: item.symbol });
    return `${path}?${new URLSearchParams({ currency: item.currency }).toString()}`;
  }

  function toggleChecked(id: number, isChecked: boolean): void {
    checkedIds = isChecked ? [...checkedIds, id] : checkedIds.filter((checkedId) => checkedId !== id);
  }

  function openRow(event: MouseEvent, id: number): void {
    // The checkbox and the links in the row do their own action.
    if (event.target instanceof Element && event.target.closest('a, input, label') !== null) {
      return;
    }
    void goto(resolve('/backtests/[backtestId]', { backtestId: String(id) }));
  }

  // A round trip starts when the position leaves 0 and ends when it is 0 again. A won round trip has a profit
  // after commissions.
  function computeWinRate(trades: BacktestTrade[]): string {
    let positionShares = 0;
    let cashUsd = 0;
    let roundTrips = 0;
    let wins = 0;
    for (const trade of trades) {
      const quantity = Number(trade.quantity_shares);
      const value = quantity * Number(trade.price_usd);
      const signedQuantity = trade.side === 'BUY' ? quantity : -quantity;
      cashUsd += (trade.side === 'BUY' ? -value : value) - Number(trade.commission_usd);
      positionShares += signedQuantity;
      if (positionShares === 0) {
        roundTrips += 1;
        wins += cashUsd > 0 ? 1 : 0;
        cashUsd = 0;
      }
    }
    return roundTrips === 0 ? '–' : `${((wins / roundTrips) * PERCENT).toFixed(1)} %`;
  }

  function readMetricTiles(detail: BacktestDetail): { name: string; value: string; tone?: 'positive' | 'negative' }[] {
    const metrics = detail.metrics;
    if (metrics === null) {
      return [];
    }
    const netProfit = Number(metrics.final_equity_usd) - Number(detail.paper_capital_usd);
    const totalReturn = Number(metrics.total_return_percent);
    return [
      {
        name: 'Total return',
        value: formatPercent(metrics.total_return_percent),
        tone: totalReturn >= 0 ? 'positive' : 'negative',
      },
      {
        name: 'Net profit (USD)',
        value: `${netProfit > 0 ? '+' : ''}${formatUsd(String(netProfit))}`,
        tone: netProfit >= 0 ? 'positive' : 'negative',
      },
      { name: 'Max drawdown', value: formatPercent(String(-Number(metrics.max_drawdown_percent))) },
      { name: 'Win rate', value: computeWinRate(detail.trades) },
      { name: 'Trades', value: String(metrics.trade_count) },
      { name: 'Final equity (USD)', value: formatUsd(metrics.final_equity_usd) },
    ];
  }

  function clampPanelHeight(heightPixels: number): number {
    const mainHeight = mainElement?.clientHeight ?? Number.POSITIVE_INFINITY;
    return Math.max(MIN_PANEL_HEIGHT_PIXELS, Math.min(heightPixels, mainHeight - MIN_CHART_HEIGHT_PIXELS));
  }

  function startSplitterDrag(event: PointerEvent): void {
    if (!(event.currentTarget instanceof HTMLElement)) {
      return;
    }
    event.currentTarget.setPointerCapture(event.pointerId);
    dragStart = { pointerYPixels: event.clientY, panelHeightPixels };
  }

  function moveSplitter(event: PointerEvent): void {
    if (dragStart === undefined) {
      return;
    }
    panelHeightPixels = clampPanelHeight(dragStart.panelHeightPixels - (event.clientY - dragStart.pointerYPixels));
  }

  function endSplitterDrag(): void {
    dragStart = undefined;
  }

  function moveSplitterWithKey(event: KeyboardEvent): void {
    const steps: Record<string, number> = { ArrowUp: KEYBOARD_STEP_PIXELS, ArrowDown: -KEYBOARD_STEP_PIXELS };
    const step = steps[event.key];
    if (step === undefined) {
      return;
    }
    event.preventDefault();
    panelHeightPixels = clampPanelHeight(panelHeightPixels + step);
  }

  async function startForwardTestFromBacktest(detail: BacktestDetail): Promise<void> {
    if (!isLiveBarPeriod(detail.bar_period) || isStartingForwardTest) {
      return;
    }
    isStartingForwardTest = true;
    forwardTestMessage = '';
    const result = await startForwardTest(fetch, {
      strategy_version_id: detail.strategy_version_id,
      symbol: detail.symbol,
      exchange: detail.exchange,
      currency: detail.currency,
      bar_period: detail.bar_period,
    });
    isStartingForwardTest = false;
    if (result.kind === 'failed') {
      forwardTestMessage = result.message;
      return;
    }
    await goto(resolve('/forward-tests/[forwardTestId]', { forwardTestId: String(result.forwardTest.id) }));
  }

  function describeForwardTestButton(detail: BacktestDetail): string {
    if (!isLiveBarPeriod(detail.bar_period)) {
      return `Start forward test: not available for ${formatBarPeriod(detail.bar_period)} bars`;
    }
    return isStartingForwardTest ? 'Starting forward test' : 'Start forward test';
  }
</script>

<div class="workbench">
  <aside class="list-column" aria-label="Backtests">
    <section class={['cds--table-toolbar', 'cds--layout--size-sm']} aria-label="Backtest list toolbar">
      <div
        class={['cds--batch-actions', showsBatchActions && 'cds--batch-actions--active']}
        aria-hidden={!showsBatchActions}
      >
        <div class="cds--batch-summary">
          <p class="cds--batch-summary__para">
            {#if comparison.kind === 'ready'}
              2 selected
            {:else if checkedIds.length > COMPARED_BACKTEST_COUNT}
              Select only 2
            {:else}
              Different strategies
            {/if}
          </p>
        </div>
        <div class="cds--action-list">
          {#if comparison.kind === 'ready'}
            <a
              class="cds--btn cds--btn--primary cds--btn--sm cds--layout--size-sm"
              href={resolve('/backtests/[backtestId]/comparison/[otherBacktestId]', {
                backtestId: String(comparison.firstBacktestId),
                otherBacktestId: String(comparison.secondBacktestId),
              })}
              tabindex={showsBatchActions ? 0 : -1}>Compare</a
            >
          {:else}
            <button type="button" class="cds--btn cds--btn--primary cds--btn--sm cds--layout--size-sm" disabled>Compare</button>
          {/if}
          <button
            type="button"
            class="cds--btn cds--btn--primary cds--btn--sm cds--layout--size-sm cds--batch-summary__cancel"
            tabindex={showsBatchActions ? 0 : -1}
            onclick={() => {
              checkedIds = [];
            }}>Cancel</button
          >
        </div>
      </div>
      <div class="cds--toolbar-content">
        <Tooltip text="New backtest" align="bottom-end">
          {#snippet trigger({ props })}
            <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- the path is resolved; only the search is added. -->
            <a href={`${resolve('/backtests')}?variant=current#start-backtest`}
              {...props}
              class="cds--btn cds--btn--ghost cds--btn--icon-only cds--btn--sm cds--layout--size-sm toolbar-icon"
              aria-label="New backtest"
            >
              <Icon icon={Add16} class="cds--btn__icon" />
            </a>
          {/snippet}
        </Tooltip>
      </div>
    </section>

    <div class="fill">
      {#if listMessage !== ''}
        <InlineNotification kind="error" title="Backtests not read" subtitle={listMessage} lowContrast />
      {:else}
        <ScrollRegion label="Backtest list" maxHeight="100%">
          <DataTable columns={LIST_COLUMNS} size="sm">
            {#snippet rows()}
              {#each backtests as item (item.id)}
                <tr class:row-open={item.id === backtestId} onclick={(event) => {
                    openRow(event, item.id);
                  }}>
                  <td class="cds--table-column-checkbox">
                    <Checkbox
                      label={`Select backtest ${String(item.id)}`}
                      hideLabel
                      checked={checkedIds.includes(item.id)}
                      onCheckedChange={(isChecked: boolean) => {
                        toggleChecked(item.id, isChecked);
                      }}
                    />
                  </td>
                  <td align="right">
                    <a
                      class="row-link"
                      href={resolve('/backtests/[backtestId]', { backtestId: String(item.id) })}
                      aria-current={item.id === backtestId ? 'page' : undefined}>{item.id}</a
                    >
                  </td>
                  <td>{formatVersionLabel(item.strategy_name, item.version_number)}</td>
                  <td>{item.symbol}</td>
                  <td>
                    <StatusIndicator label={describeBacktestStatus(item.status)} kind={findBacktestStatusKind(item.status)} />
                  </td>
                  <td align="right">{item.metrics === null ? '' : formatPercent(item.metrics.total_return_percent)}</td>
                </tr>
              {/each}
            {/snippet}
          </DataTable>
        </ScrollRegion>
      {/if}
    </div>
  </aside>

  <div class={['main', `main--${panelLayout}`]} bind:this={mainElement}>
    {#if detailMessage !== ''}
      <InlineNotification kind="error" title="Backtest not read" subtitle={detailMessage} lowContrast />
    {/if}

    {#if shownBacktest === null}
      <div class="empty-main"></div>
    {:else}
      {@const detail = shownBacktest}
      {@const tiles = readMetricTiles(detail)}
      <section class="panel chart-panel" aria-label="Chart panel">
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <header
        class="run-header"
        ondblclick={(event) => {
          toggleMaximizeFromHeader(event, 'chart');
        }}
      >
        <h1 class="run-title">
          <span class="run-number">#{detail.id}</span>
          <a class="cds--link" href={resolve('/strategies/[strategyId]', { strategyId: String(detail.strategy_id) })}
            >{formatVersionLabel(detail.strategy_name, detail.version_number)}</a
          >
          <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- instrumentHref resolved the path. -->
          <a class="cds--link" href={instrumentHref(detail)}>{detail.symbol}</a>
          <span class="run-period">{formatBarPeriod(detail.bar_period)}</span>
        </h1>
        <span role="status" class="run-status">
          <StatusIndicator label={describeBacktestStatus(detail.status)} kind={findBacktestStatusKind(detail.status)} />
        </span>
        <span class="run-actions">
          <Tooltip text={describeForwardTestButton(detail)} align="bottom-end">
            {#snippet trigger({ props })}
              <button
                {...props}
                type="button"
                class={[
                  'cds--btn',
                  'cds--btn--ghost',
                  'cds--btn--icon-only',
                  'cds--btn--sm',
                  'cds--layout--size-sm',
                  'forward-test-button',
                  !isLiveBarPeriod(detail.bar_period) && 'cds--btn--disabled',
                ]}
                aria-label={describeForwardTestButton(detail)}
                aria-disabled={!isLiveBarPeriod(detail.bar_period) || isStartingForwardTest}
                onclickcapture={() => {
                  void startForwardTestFromBacktest(detail);
                }}
              >
                <Icon icon={ConnectionSignal16} class="cds--btn__icon" />
              </button>
            {/snippet}
          </Tooltip>
          {#if detail.metrics !== null}
            {@render panelControls('chart')}
          {/if}
        </span>
      </header>

      {#if forwardTestMessage !== ''}
        <InlineNotification
          kind="error"
          title="Forward test not started"
          subtitle={forwardTestMessage}
          lowContrast
          onClose={() => {
            forwardTestMessage = '';
          }}
        />
      {/if}

      {#if detail.metrics === null}
        <div class="state-area" role="status">
          <StatusIndicator label={describeBacktestStatus(detail.status)} kind={findBacktestStatusKind(detail.status)} />
        </div>
      {:else}
        <dl class="metric-row" aria-label="Metrics">
          {#each tiles as tile (tile.name)}
            <div class="cds--tile metric">
              <dt>{tile.name}</dt>
              <dd class={tile.tone === undefined ? undefined : `metric--${tile.tone}`}>{tile.value}</dd>
            </div>
          {/each}
        </dl>

        <div class="chart-area">
          {#key detail.id}
            <BacktestEquityDrawdownChart points={detail.equity_curve} label="Equity and drawdown" />
          {/key}
        </div>
      {/if}
      </section>

      {#if detail.metrics !== null}
        {#if panelLayout === 'split'}
        <!-- svelte-ignore a11y_no_noninteractive_tabindex, a11y_no_noninteractive_element_interactions -->
        <div
          class="splitter"
          role="separator"
          aria-orientation="horizontal"
          aria-label="Resize the tables"
          aria-valuenow={panelHeightPixels}
          tabindex="0"
          onpointerdown={startSplitterDrag}
          onpointermove={moveSplitter}
          onpointerup={endSplitterDrag}
          onpointercancel={endSplitterDrag}
          onkeydown={moveSplitterWithKey}
        ></div>
        {/if}

        <section
          class="panel bottom-panel"
          aria-label="Tables panel"
          style:block-size={panelLayout === 'split' ? `${String(panelHeightPixels)}px` : undefined}
          ondblclick={(event) => {
            if (event.target instanceof Element && event.target.closest('.cds--tabs') !== null) {
              toggleMaximizeFromHeader(event, 'tables');
            }
          }}
        >
          <div class="panel-controls-overlay">{@render panelControls('tables')}</div>
          <Tabs label="Backtest tables" items={TAB_ITEMS} value={selectedTab} onValueChange={(value: string) => {
              selectedTab = value;
            }}>
            {#snippet panel()}
              <div class="tab-fill">
                {#if selectedTab === 'trades'}
                  {#if detail.trades.length === 0}
                    <p class="empty-word">No trades</p>
                  {:else}
                    <ScrollRegion label="Trades" maxHeight="100%">
                      <DataTable columns={TRADE_COLUMNS} size="sm">
                        {#snippet rows()}
                          {#each detail.trades as trade, tradeIndex (tradeIndex)}
                            <tr>
                              <td align="right">{tradeIndex + 1}</td>
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
                {:else if selectedTab === 'orders'}
                  <p class="empty-word">No orders</p>
                {:else if detail.error_message !== null}
                  <ScrollRegion label="Logs" maxHeight="100%">
                    <pre class="log-text">{detail.error_message}</pre>
                  </ScrollRegion>
                {:else}
                  <p class="empty-word">No logs</p>
                {/if}
              </div>
            {/snippet}
          </Tabs>
        </section>
      {/if}
    {/if}
  </div>
</div>

<svelte:window onkeydown={restoreWithEscape} />

{#snippet panelButton(label: string, icon: typeof Maximize16, onAction: () => void)}
  <Tooltip text={label} align="bottom-end">
    {#snippet trigger({ props })}
      <button
        {...props}
        type="button"
        class="cds--btn cds--btn--ghost cds--btn--icon-only cds--btn--sm cds--layout--size-sm"
        aria-label={label}
        onclickcapture={onAction}
      >
        <Icon icon={icon} class="cds--btn__icon" />
      </button>
    {/snippet}
  </Tooltip>
{/snippet}

{#snippet panelControls(panel: PanelName)}
  <span class="panel-controls">
    {#if panelLayout === minimizedLayout(panel)}
      {@render panelButton('Restore panel', Subtract16, () => {
        panelLayout = 'split';
      })}
    {:else}
      {@render panelButton('Minimize panel', Subtract16, () => {
        panelLayout = minimizedLayout(panel);
      })}
    {/if}
    {#if panelLayout === maximizedLayout(panel)}
      {@render panelButton('Restore panel', Minimize16, () => {
        panelLayout = 'split';
      })}
    {:else}
      {@render panelButton('Maximize panel', Maximize16, () => {
        panelLayout = maximizedLayout(panel);
      })}
    {/if}
  </span>
{/snippet}

<style>
  .workbench {
    display: grid;
    grid-template-columns: 34rem minmax(0, 1fr);
    block-size: 100%;
    background: var(--cds-background);
  }

  /* Left column: toolbar, then the list in its own scroll region. */
  .list-column {
    display: grid;
    grid-template-rows: auto minmax(0, 1fr);
    min-block-size: 0;
    min-inline-size: 0;
    overflow: hidden;
    border-inline-end: 1px solid var(--cds-border-subtle-01);
  }

  .fill,
  .tab-fill {
    min-block-size: 0;
    block-size: 100%;
  }

  .fill :global(.scroll-region),
  .tab-fill :global(.scroll-region) {
    block-size: 100%;
  }

  .fill :global(thead th),
  .tab-fill :global(thead th) {
    position: sticky;
    inset-block-start: 0;
    z-index: 1;
  }

  .toolbar-icon {
    color: var(--cds-icon-primary);
  }

  .list-column :global(tbody tr) {
    cursor: pointer;
  }

  .list-column :global(td) {
    white-space: nowrap;
  }

  .row-link {
    color: inherit;
    text-decoration: none;
  }

  .row-link:focus-visible {
    outline: 2px solid var(--cds-focus);
    outline-offset: -2px;
  }

  /* The open backtest: the Carbon selected row color and an interactive bar at the start of the row. */
  .list-column :global(tr.row-open td) {
    background: var(--cds-layer-selected-01);
    color: var(--cds-text-primary);
  }

  .list-column :global(tr.row-open td:first-child) {
    box-shadow: inset 3px 0 0 var(--cds-border-interactive);
  }

  /* Main area: header, metric row, chart (fills the rest), splitter, tables. */
  .main {
    display: flex;
    flex-direction: column;
    min-block-size: 0;
    min-inline-size: 0;
  }

  .empty-main {
    flex: 1;
  }

  .panel {
    display: flex;
    flex-direction: column;
    min-block-size: 0;
  }

  .chart-panel {
    flex: 1;
  }

  /* A minimized panel shows only its header line. */
  .main--tables-max .chart-panel {
    flex: none;
  }

  .main--tables-max .chart-panel > :not(.run-header) {
    display: none;
  }

  .main--chart-max .bottom-panel :global(.cds--tab-content) {
    display: none;
  }

  .main--tables-max .bottom-panel {
    flex: 1;
  }

  .main--tables-max .bottom-panel :global([data-tabs-root]) {
    flex: 1;
  }

  .panel-controls {
    display: inline-flex;
  }

  .panel-controls-overlay {
    position: absolute;
    z-index: 2;
    inset-block-start: 0;
    inset-inline-end: var(--cds-spacing-03);
    display: flex;
    align-items: center;
    block-size: var(--cds-spacing-08);
  }

  .run-header {
    display: flex;
    flex: none;
    align-items: center;
    gap: var(--cds-spacing-05);
    block-size: var(--cds-spacing-07);
    padding-inline: var(--cds-spacing-05) var(--cds-spacing-03);
    border-block-end: 1px solid var(--cds-border-subtle-01);
  }

  .run-title {
    display: flex;
    align-items: baseline;
    gap: var(--cds-spacing-04);
    margin: 0;
    font-size: var(--cds-heading-compact-02-font-size);
    font-weight: var(--cds-heading-compact-02-font-weight);
    line-height: var(--cds-heading-compact-02-line-height);
    letter-spacing: var(--cds-heading-compact-02-letter-spacing);
    white-space: nowrap;
  }

  /* One type size in the heading: Carbon links set their own size. */
  .run-title > :global(*) {
    font: inherit;
    letter-spacing: inherit;
  }

  .run-number {
    font-variant-numeric: tabular-nums;
    color: var(--cds-text-secondary);
  }

  .run-period {
    color: var(--cds-text-secondary);
  }

  .run-status {
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
  }

  .run-actions {
    display: inline-flex;
    gap: var(--cds-spacing-03);
    margin-inline-start: auto;
  }

  .forward-test-button:not(.cds--btn--disabled) {
    color: var(--cds-icon-interactive);
  }

  .state-area {
    display: flex;
    flex: 1;
    align-items: center;
    justify-content: center;
    font-size: var(--cds-heading-compact-02-font-size);
    line-height: var(--cds-heading-compact-02-line-height);
  }

  .metric-row {
    display: grid;
    flex: none;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 1px;
    margin: 0;
    background: var(--cds-border-subtle-01);
    border-block-end: 1px solid var(--cds-border-subtle-01);
  }

  .metric {
    min-block-size: 0;
    padding: var(--cds-spacing-03) var(--cds-spacing-05);
  }

  .metric dt {
    font-size: var(--cds-label-01-font-size);
    line-height: var(--cds-label-01-line-height);
    letter-spacing: var(--cds-label-01-letter-spacing);
    color: var(--cds-text-secondary);
  }

  .metric dd {
    margin: var(--cds-spacing-02) 0 0;
    font-size: var(--cds-heading-compact-02-font-size);
    font-weight: var(--cds-heading-compact-02-font-weight);
    line-height: var(--cds-heading-compact-02-line-height);
    font-variant-numeric: tabular-nums;
    text-align: end;
  }

  .metric--positive {
    color: var(--cds-support-success);
  }

  .metric--negative {
    color: var(--cds-support-error);
  }

  .chart-area {
    position: relative;
    flex: 1;
    min-block-size: 0;
  }

  .splitter {
    flex: none;
    block-size: var(--cds-spacing-02);
    background: var(--cds-border-subtle-01);
    cursor: row-resize;
    touch-action: none;
  }

  .splitter:hover,
  .splitter:focus-visible {
    background: var(--cds-border-interactive);
    outline: none;
  }

  .bottom-panel {
    position: relative;
    flex: none;
    min-block-size: 0;
  }

  .bottom-panel :global([data-tabs-root]) {
    display: grid;
    grid-template-rows: auto minmax(0, 1fr);
    block-size: 100%;
  }

  .bottom-panel :global(.cds--tab-content) {
    min-block-size: 0;
    padding: 0;
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
