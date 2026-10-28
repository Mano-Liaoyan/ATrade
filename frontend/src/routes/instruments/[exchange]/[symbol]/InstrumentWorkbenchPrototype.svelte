<!-- PROTOTYPE (#99), throwaway: the instrument page as a 3-column workbench (issue #99, sections 2, 4, 5, 6, 7).
     Left: the watchlist. Center: price line with the bar period tabs, the bar chart that fills the height, a splitter,
     and the paper account tabs. Right: the paper order panel. The page does not scroll; each region scrolls. -->
<script lang="ts">
  import ArrowDown16 from '@carbon/icons/es/arrow--down/16.js';
  import ArrowUp16 from '@carbon/icons/es/arrow--up/16.js';
  import Maximize16 from '@carbon/icons/es/maximize/16.js';
  import Minimize16 from '@carbon/icons/es/minimize/16.js';
  import RightPanelClose16 from '@carbon/icons/es/right-panel--close/16.js';
  import RightPanelOpen16 from '@carbon/icons/es/right-panel--open/16.js';
  import SidePanelClose16 from '@carbon/icons/es/side-panel--close/16.js';
  import SidePanelOpen16 from '@carbon/icons/es/side-panel--open/16.js';
  import Subtract16 from '@carbon/icons/es/subtract/16.js';
  import { ContentSwitcher, Icon } from '#lib/foundation/carbon';
  import { buildSocketUrl, openLiveSocket } from '#lib/foundation/live_socket';
  import { BAR_PERIODS, BarChart, formatInstrument, readBars, type Bar, type ChartRequest } from '#lib/market_data';
  import {
    PAPER_TRADING_SOCKET_PATH,
    readFilledManualOrders,
    readOpenOrdersMessage,
    readPaperAccountMessage,
    type ManualOrder,
    type OpenOrder,
    type PaperAccountMessage,
  } from '#lib/paper_trading';
  import { findChangeDirection, formatChange, formatPrice, readDayQuote, type DayQuote } from './instrument_quote';
  import WorkbenchAccountTabs from './WorkbenchAccountTabs.svelte';
  import WorkbenchOrderPanel from './WorkbenchOrderPanel.svelte';
  import WorkbenchWatchlist from './WorkbenchWatchlist.svelte';
  import PanelIconButton from './PanelIconButton.svelte';
  import {
    isEmptyHeaderTarget,
    isHeaderOnly,
    readPanelLayout,
    toggleCenterMode,
    writePanelLayout,
    type CenterPanel,
  } from './workbench_panels';

  interface Props {
    chartRequest: ChartRequest;
    bars: Bar[];
    liveBar: Bar | null;
    isLoading: boolean;
    barsError: string | null;
    liveBarError: string | null;
    onBarPeriodChange: (value: string) => void;
  }

  const { chartRequest, bars, liveBar, isLoading, barsError, liveBarError, onBarPeriodChange }: Props = $props();

  const instrumentName = $derived(formatInstrument(chartRequest.instrument));

  // The price line uses the 1-DAY bars: the change is from the close of the previous day.
  let dayQuote = $state<DayQuote | null>(null);
  $effect(() => {
    const { instrument } = chartRequest;
    let isCurrent = true;
    dayQuote = null;
    void readBars(fetch, instrument, '1-DAY').then((result) => {
      if (isCurrent && result.kind === 'loaded') {
        dayQuote = readDayQuote(result.bars);
      }
    });
    return () => {
      isCurrent = false;
    };
  });
  const lastPrice = $derived(liveBar?.close ?? dayQuote?.last ?? bars.at(-1)?.close ?? null);
  const changeDirection = $derived(findChangeDirection(dayQuote?.change ?? null));

  // The paper account: positions and balance, open orders, and filled orders by hand.
  let account = $state<PaperAccountMessage | null>(null);
  let openOrders = $state<OpenOrder[]>([]);
  let filledOrders = $state<ManualOrder[]>([]);

  async function refreshFilledOrders(): Promise<void> {
    const orders = await readFilledManualOrders(fetch);
    if (orders !== null) {
      filledOrders = orders;
    }
  }

  $effect(() => {
    void refreshFilledOrders();
    return openLiveSocket({
      url: buildSocketUrl(PAPER_TRADING_SOCKET_PATH, window.location),
      onMessage: (message) => {
        const accountMessage = readPaperAccountMessage(message);
        if (accountMessage !== null) {
          account = accountMessage;
        }
        const ordersMessage = readOpenOrdersMessage(message);
        if (ordersMessage !== null) {
          openOrders = ordersMessage;
          void refreshFilledOrders();
        }
      },
      onConnectionChange: () => undefined,
    });
  });

  // The splitter between the chart and the tabs. A pointer drag or the arrow keys change the tab panel height.
  const MIN_PANEL_PIXELS = 96;
  const MIN_CHART_PIXELS = 160;
  const KEY_STEP_PIXELS = 16;

  // The panel layout: minimized or maximized center panels, collapsed side columns, and the account panel height.
  const layout = $state(readPanelLayout());
  $effect(() => {
    writePanelLayout({ ...layout });
  });

  let centerHeight = $state(0);
  let panelHeight = $state(layout.accountPanelPixels);
  $effect(() => {
    layout.accountPanelPixels = panelHeight;
  });

  const isChartHeaderOnly = $derived(isHeaderOnly(layout.center, 'chart'));
  const isAccountHeaderOnly = $derived(isHeaderOnly(layout.center, 'account'));
  const centerRows = $derived.by(() => {
    if (isChartHeaderOnly) {
      return 'auto minmax(0, 1fr)';
    }
    if (isAccountHeaderOnly) {
      return 'minmax(0, 1fr) auto';
    }
    return `minmax(0, 1fr) auto ${String(shownPanelHeight)}px`;
  });

  function toggleMinimized(panel: CenterPanel): void {
    layout.center = toggleCenterMode(layout.center, panel, 'minimized');
  }

  function toggleMaximized(panel: CenterPanel): void {
    layout.center = toggleCenterMode(layout.center, panel, 'maximized');
  }

  // Escape restores a maximized panel. A dialog or a menu uses Escape first.
  function restoreOnEscape(event: KeyboardEvent): void {
    const isInPopup = event.target instanceof Element && event.target.closest('[role="dialog"], [role="menu"], [role="listbox"]') !== null;
    if (event.key === 'Escape' && !event.defaultPrevented && !isInPopup && layout.center.endsWith('-maximized')) {
      layout.center = 'split';
    }
  }

  function toggleChartOnDoubleClick(event: MouseEvent): void {
    if (event.currentTarget instanceof HTMLElement && isEmptyHeaderTarget(event.target, event.currentTarget)) {
      toggleMaximized('chart');
    }
  }
  let dragStart: { pointerY: number; panelHeight: number } | null = null;

  const maxPanelHeight = $derived(Math.max(MIN_PANEL_PIXELS, centerHeight - MIN_CHART_PIXELS));
  const shownPanelHeight = $derived(Math.min(Math.max(panelHeight, MIN_PANEL_PIXELS), maxPanelHeight));

  function clampPanelHeight(height: number): number {
    return Math.min(Math.max(height, MIN_PANEL_PIXELS), maxPanelHeight);
  }

  function startSplitterDrag(event: PointerEvent): void {
    if (!(event.currentTarget instanceof HTMLElement)) {
      return;
    }
    event.currentTarget.setPointerCapture(event.pointerId);
    dragStart = { pointerY: event.clientY, panelHeight: shownPanelHeight };
  }

  function moveSplitter(event: PointerEvent): void {
    if (dragStart === null) {
      return;
    }
    panelHeight = clampPanelHeight(dragStart.panelHeight - (event.clientY - dragStart.pointerY));
  }

  function endSplitterDrag(): void {
    dragStart = null;
  }

  function moveSplitterWithKey(event: KeyboardEvent): void {
    const stepByKey: Record<string, number> = {
      ArrowUp: KEY_STEP_PIXELS,
      ArrowDown: -KEY_STEP_PIXELS,
      Home: maxPanelHeight,
      End: -maxPanelHeight,
    };
    const step = stepByKey[event.key];
    if (step === undefined) {
      return;
    }
    event.preventDefault();
    panelHeight = clampPanelHeight(shownPanelHeight + step);
  }

  // TradingView-style short bar period names, so that all periods fit on the price line.
  const SHORT_NAMES: Record<string, string> = {
    '1-MINUTE': '1m',
    '5-MINUTE': '5m',
    '15-MINUTE': '15m',
    '30-MINUTE': '30m',
    '1-HOUR': '1h',
    '1-DAY': '1D',
  };
  const SHORT_BAR_PERIODS = BAR_PERIODS.map((period) => ({ value: period.value, label: SHORT_NAMES[period.value] ?? period.label }));
</script>

<svelte:window onkeydown={restoreOnEscape} />

{#snippet panelActions(panel: CenterPanel)}
  {@const isMinimized = layout.center === `${panel}-minimized`}
  {@const isMaximized = layout.center === `${panel}-maximized`}
  <PanelIconButton
    label={isMinimized ? 'Restore panel' : 'Minimize panel'}
    icon={isMinimized ? Minimize16 : Subtract16}
    onclick={() => {
      toggleMinimized(panel);
    }}
  />
  <PanelIconButton
    label={isMaximized ? 'Restore panel' : 'Maximize panel'}
    icon={isMaximized ? Minimize16 : Maximize16}
    onclick={() => {
      toggleMaximized(panel);
    }}
  />
{/snippet}

<div
  class="workbench"
  style:grid-template-columns={`${layout.isWatchlistCollapsed ? 'var(--cds-spacing-07)' : '17.5rem'} minmax(0, 1fr) ${
    layout.isOrderPanelCollapsed ? 'var(--cds-spacing-07)' : '20rem'
  }`}
>
  <aside class={['column', 'column--watchlist', layout.isWatchlistCollapsed && 'column--rail']}>
    {#if layout.isWatchlistCollapsed}
      <PanelIconButton
        label="Open watchlist"
        icon={SidePanelOpen16}
        align="right"
        onclick={() => {
          layout.isWatchlistCollapsed = false;
        }}
      />
    {/if}
    <div class="column-header" hidden={layout.isWatchlistCollapsed}>
      <h2>Watchlist</h2>
      <PanelIconButton
        label="Collapse watchlist"
        icon={SidePanelClose16}
        onclick={() => {
          layout.isWatchlistCollapsed = true;
        }}
      />
    </div>
    <div class="column-body" hidden={layout.isWatchlistCollapsed}>
      <WorkbenchWatchlist instrument={chartRequest.instrument} barPeriod={chartRequest.barPeriod} />
    </div>
  </aside>

  <section class="center" aria-label={instrumentName} style:grid-template-rows={centerRows} bind:clientHeight={centerHeight}>
    <div class={['chart-panel', isChartHeaderOnly && 'chart-panel--header-only']}>
    <!-- Double-click is a pointer shortcut. The maximize button is the keyboard path. -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <header class="price-line" ondblclick={toggleChartOnDoubleClick}>
      <h1>{instrumentName}</h1>
      <span class="last-price" aria-label="Last price">{formatPrice(lastPrice)}</span>
      {#if dayQuote !== null}
        <span class={`change change--${changeDirection}`} aria-label="Change from the previous close">
          {#if changeDirection === 'up'}
            <Icon icon={ArrowUp16} />
          {:else if changeDirection === 'down'}
            <Icon icon={ArrowDown16} />
          {/if}
          {formatChange(dayQuote)}
        </span>
      {/if}
      <div class="bar-periods">
        <ContentSwitcher
          label="Bar period"
          size="sm"
          items={SHORT_BAR_PERIODS}
          value={chartRequest.barPeriod}
          onValueChange={onBarPeriodChange}
        />
      </div>
      <div class="panel-actions">{@render panelActions('chart')}</div>
    </header>

    <div class="chart">
      <BarChart bars={bars} {liveBar} label="Bar chart of {instrumentName}, {chartRequest.barPeriod} bars" />
      {#if isLoading}
        <p class="chart-status" role="status">Loading bars.</p>
      {:else if barsError !== null}
        <p class="chart-status chart-status--error" role="alert">{barsError}</p>
      {:else if liveBarError !== null}
        <p class="chart-status chart-status--error" role="alert">No live bars. {liveBarError}</p>
      {/if}
    </div>
    </div>

    {#if layout.center === 'split'}
    <!-- A focusable separator is a widget in WAI-ARIA (window splitter pattern); Svelte treats every separator as static. -->
    <!-- svelte-ignore a11y_no_noninteractive_tabindex, a11y_no_noninteractive_element_interactions -->
    <div
      class="splitter"
      role="separator"
      tabindex="0"
      aria-label="Resize the chart and the account tabs"
      aria-orientation="horizontal"
      aria-valuemin={MIN_PANEL_PIXELS}
      aria-valuemax={maxPanelHeight}
      aria-valuenow={shownPanelHeight}
      onpointerdown={startSplitterDrag}
      onpointermove={moveSplitter}
      onpointerup={endSplitterDrag}
      onpointercancel={endSplitterDrag}
      onkeydown={moveSplitterWithKey}
    ></div>
    {/if}

    <div class="account">
      <WorkbenchAccountTabs
        positions={account?.positions ?? null}
        {openOrders}
        {filledOrders}
        headerOnly={isAccountHeaderOnly}
        onTabSelect={() => {
          if (isAccountHeaderOnly) {
            layout.center = 'split';
          }
        }}
        onHeaderDoubleClick={() => {
          toggleMaximized('account');
        }}
      >
        {#snippet actions()}
          {@render panelActions('account')}
        {/snippet}
      </WorkbenchAccountTabs>
    </div>
  </section>

  <aside class={['column', 'column--order', layout.isOrderPanelCollapsed && 'column--rail']} aria-label="Paper order">
    {#if layout.isOrderPanelCollapsed}
      <PanelIconButton
        label="Open order panel"
        icon={RightPanelOpen16}
        align="left"
        onclick={() => {
          layout.isOrderPanelCollapsed = false;
        }}
      />
    {/if}
    <div class="column-header" hidden={layout.isOrderPanelCollapsed}>
      <h2>Paper order</h2>
      <PanelIconButton
        label="Collapse order panel"
        icon={RightPanelClose16}
        onclick={() => {
          layout.isOrderPanelCollapsed = true;
        }}
      />
    </div>
    <div class="column-body" hidden={layout.isOrderPanelCollapsed}>
      <WorkbenchOrderPanel instrument={chartRequest.instrument} {lastPrice} {account} />
    </div>
  </aside>
</div>

<style>
  /* PROTOTYPE (#99): the page fills <main>. Each column and each region has min-block-size 0, so they can scroll. */
  .workbench {
    display: grid;
    block-size: 100%;
    min-block-size: 0;
    background: var(--cds-background);
  }

  .column {
    display: grid;
    grid-template-rows: auto minmax(0, 1fr);
    min-block-size: 0;
    min-inline-size: 0;
    overflow: hidden;
  }

  /* A collapsed column is a 2rem rail with the button that opens it again. */
  .column--rail {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding-block-start: var(--cds-spacing-02);
  }

  .column [hidden] {
    display: none;
  }

  /* Every panel header line has the Carbon tab height, so the lines of the 3 columns align. */
  .column-header,
  .price-line {
    box-sizing: border-box;
    block-size: var(--cds-spacing-08);
    border-block-end: 1px solid var(--cds-border-subtle-01);
  }

  .column-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-inline: var(--cds-spacing-05) var(--cds-spacing-02);
  }

  h2 {
    margin: 0;
    font-size: var(--cds-heading-compact-01-font-size);
    font-weight: var(--cds-heading-compact-01-font-weight);
    line-height: var(--cds-heading-compact-01-line-height);
    letter-spacing: var(--cds-heading-compact-01-letter-spacing);
  }

  .column-body {
    min-block-size: 0;
  }

  .chart-panel {
    display: grid;
    grid-template-rows: auto minmax(0, 1fr);
    min-block-size: 0;
  }

  .chart-panel--header-only .chart {
    display: none;
  }

  .panel-actions {
    display: flex;
    flex: none;
  }

  .column--watchlist {
    border-inline-end: 1px solid var(--cds-border-subtle-01);
  }

  .column--order {
    border-inline-start: 1px solid var(--cds-border-subtle-01);
  }

  .center {
    display: grid;
    min-block-size: 0;
    min-inline-size: 0;
  }

  .price-line {
    display: flex;
    align-items: center;
    gap: var(--cds-spacing-05);
    min-inline-size: 0;
    padding-inline: var(--cds-spacing-05) var(--cds-spacing-02);
  }

  h1 {
    margin: 0;
    font-size: var(--cds-heading-compact-02-font-size);
    font-weight: var(--cds-heading-compact-02-font-weight);
    line-height: var(--cds-heading-compact-02-line-height);
    letter-spacing: var(--cds-heading-compact-02-letter-spacing);
    white-space: nowrap;
  }

  .last-price {
    font-size: var(--cds-heading-compact-02-font-size);
    line-height: var(--cds-heading-compact-02-line-height);
    font-variant-numeric: tabular-nums;
  }

  .change {
    display: inline-flex;
    align-items: center;
    gap: var(--cds-spacing-02);
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
    color: var(--cds-text-secondary);
  }

  .change--up {
    color: var(--cds-support-success);
  }

  .change--down {
    color: var(--cds-support-error);
  }

  .change :global(svg) {
    fill: currentcolor;
  }

  .bar-periods :global(.cds--content-switcher) {
    inline-size: calc(var(--cds-spacing-10) * 5);
  }

  .bar-periods :global(.cds--content-switcher-btn) {
    padding-inline: var(--cds-spacing-03);
    justify-content: center;
  }

  .bar-periods {
    flex: none;
    margin-inline-start: auto;
    min-inline-size: 0;
  }

  /* The bar chart fills the row. BarChart sets a fixed canvas height for the document page; the workbench removes it. */
  .chart {
    position: relative;
    min-block-size: 0;
  }

  .chart :global(.bar-chart) {
    display: flex;
    flex-direction: column;
    block-size: 100%;
    padding: var(--cds-spacing-03) var(--cds-spacing-05);
    box-sizing: border-box;
  }

  .chart :global(.chart-canvas) {
    flex: 1;
    height: auto;
    min-height: 0;
  }

  .chart :global(.chart-attribution) {
    margin-block-start: var(--cds-spacing-02);
  }

  .chart-status {
    position: absolute;
    inset-block-start: var(--cds-spacing-05);
    inset-inline-start: var(--cds-spacing-07);
    margin: 0;
    padding: var(--cds-spacing-02) var(--cds-spacing-03);
    background: var(--cds-layer-01);
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
    color: var(--cds-text-secondary);
  }

  .chart-status--error {
    color: var(--cds-text-error);
  }

  .splitter {
    block-size: var(--cds-spacing-02);
    background: var(--cds-border-subtle-01);
    cursor: row-resize;
    touch-action: none;
  }

  .splitter:hover {
    background: var(--cds-border-strong-01);
  }

  .splitter:focus-visible {
    outline: 2px solid var(--cds-focus);
    outline-offset: -2px;
  }

  .account {
    min-block-size: 0;
    overflow: hidden;
  }
</style>
