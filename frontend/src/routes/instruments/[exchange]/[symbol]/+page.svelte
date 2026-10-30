<!-- Instrument page: a workbench (foundation/workbench, #102) that fills the window below the header.
     Left: the watchlist column. Center: the chart panel (name, last price, change, the bar period switcher, and the
     bar chart with live bars from /ws/market-data) over the paper order panel (positions, open orders, and filled
     orders of today from /ws/paper-trading). Right: the paper order column (InstrumentOrderPanel, IBKR Desktop layout) for the instrument of the page. A watchlist instrument opens here.
     URL: /instruments/<exchange>/<symbol>?currency=<currency>&bar_period=<bar period>. -->
<script lang="ts">
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
  import { ContentSwitcher, StatusIndicator } from '#lib/foundation/carbon';
  import { buildSocketUrl, LiveUpdatesNotification, openLiveSocket } from '#lib/foundation/live_socket';
  import { ChangeText, formatPrice } from '#lib/foundation/value_format';
  import { Panel, PanelSplit, SideColumn, Workbench, type PanelSpec } from '#lib/foundation/workbench';
  import {
    BAR_PERIODS,
    BarChart,
    describeLiveBar,
    formatChartSearch,
    formatDayChange,
    formatInstrument,
    formatLiveBarsPath,
    readBars,
    readChartRequest,
    readDayQuote,
    readLiveBarMessage,
    type Bar,
    type BarPeriod,
    type BarsResult,
    type DayQuote,
  } from '#lib/market_data';
  import { FilledManualOrderList, InstrumentOrderPanel, OpenOrderList, PaperAccountFeed, PositionTable } from '#lib/paper_trading';
  import InstrumentWatchlist from '../../../InstrumentWatchlist.svelte';

  const chartRequest = $derived(readChartRequest(page.params, page.url.searchParams));

  // The bars and the live bar keep the chart request that they belong to. When the bar period changes, the chart
  // gets no data of the previous bar period, also before the effects below run again: the chart cannot draw a live
  // bar that is older than its last bar.
  const chartKey = $derived(chartRequest === null ? null : formatLiveBarsPath(chartRequest));
  let loadedBars: { key: string; result: BarsResult } | undefined = $state();
  let receivedLiveBar: { key: string; bar: Bar } | undefined = $state();
  const barsResult = $derived(loadedBars?.key === chartKey ? loadedBars.result : undefined);
  const liveBar = $derived(receivedLiveBar?.key === chartKey ? receivedLiveBar.bar : null);
  const isLoading = $derived(chartKey !== null && barsResult === undefined);
  // A new array for each chart request: the chart then removes the bars and the live bar of the previous request,
  // also while the new bars load.
  const chartBars = $derived.by(() => {
    if (chartKey === null || barsResult?.kind !== 'loaded') {
      return [];
    }
    return barsResult.bars;
  });

  $effect(() => {
    if (chartRequest === null) {
      return;
    }
    const { instrument, barPeriod } = chartRequest;
    const key = formatLiveBarsPath(chartRequest);
    let isCurrent = true;
    void readBars(fetch, instrument, barPeriod).then((result) => {
      if (isCurrent) {
        loadedBars = { key, result };
      }
    });
    return () => {
      isCurrent = false;
    };
  });

  let liveBarError: string | null = $state(null);
  let isLiveSocketConnected = $state(false);

  $effect(() => {
    if (chartRequest === null) {
      return;
    }
    const key = formatLiveBarsPath(chartRequest);
    liveBarError = null;
    // The live socket connects again after a close, a missing heartbeat, or when a background tab comes back.
    return openLiveSocket({
      url: buildSocketUrl(key, window.location),
      onMessage: (message) => {
        const liveBarMessage = readLiveBarMessage(message);
        if (liveBarMessage?.type === 'bar') {
          receivedLiveBar = { key, bar: liveBarMessage.bar };
          liveBarError = null;
        } else if (liveBarMessage?.type === 'error') {
          liveBarError = liveBarMessage.detail;
        }
      },
      onConnectionChange: (isConnected) => {
        isLiveSocketConnected = isConnected;
      },
    });
  });

  const liveBarErrorText = $derived(liveBarError === null ? null : `No live bars. ${liveBarError}`);
  const liveBarText = $derived.by(() => {
    if (liveBarErrorText !== null) {
      return liveBarErrorText;
    }
    if (liveBar !== null) {
      return describeLiveBar(liveBar);
    }
    return isLiveSocketConnected ? 'Waiting for live bars.' : 'Connecting to live bars.';
  });

  // The price line uses the daily bars: the change is from the close of the previous day.
  const instrumentKey = $derived(chartRequest === null ? null : formatInstrument(chartRequest.instrument));
  let dayQuote = $state<{ instrumentKey: string; quote: DayQuote | null } | null>(null);
  $effect(() => {
    if (chartRequest === null || instrumentKey === null) {
      return;
    }
    const key = instrumentKey;
    let isCurrent = true;
    void readBars(fetch, chartRequest.instrument, '1-DAY').then((result) => {
      if (isCurrent) {
        dayQuote = { instrumentKey: key, quote: result.kind === 'loaded' ? readDayQuote(result.bars) : null };
      }
    });
    return () => {
      isCurrent = false;
    };
  });
  const shownDayQuote = $derived(dayQuote?.instrumentKey === instrumentKey ? dayQuote.quote : null);
  const lastPrice = $derived(liveBar?.close ?? shownDayQuote?.last ?? chartBars.at(-1)?.close ?? null);

  // The paper account. Forward tests and orders by hand share the instruments (forward_test.md section 12.2).
  const accountFeed = new PaperAccountFeed();
  $effect(() => accountFeed.start(fetch, window.location));
  const account = $derived(accountFeed.account);

  const PANELS: PanelSpec[] = [
    { id: 'chart', minPixels: 160 },
    { id: 'account', minPixels: 96, defaultPixels: 240, splitterLabel: 'Resize the chart and the paper account' },
  ];

  type AccountTable = 'positions' | 'open-orders' | 'filled-today';
  let accountTable: AccountTable = $state('positions');
  const accountTabItems = $derived.by(() => {
    const counts: Record<AccountTable, number> = {
      positions: account?.positions.length ?? 0,
      'open-orders': accountFeed.openOrders.length,
      'filled-today': accountFeed.filledOrders.length,
    };
    const tabs: { value: AccountTable; label: string }[] = [
      { value: 'positions', label: 'Positions' },
      { value: 'open-orders', label: 'Open orders' },
      { value: 'filled-today', label: 'Filled today' },
    ];
    return tabs.map((tab) => ({
      value: tab.value,
      label: counts[tab.value] > 0 ? `${tab.label} (${String(counts[tab.value])})` : tab.label,
    }));
  });

  const barPeriodItems = BAR_PERIODS.map((period) => ({
    value: period.value,
    label: period.shortLabel,
    accessibleLabel: period.label,
  }));

  function changeBarPeriod(barPeriod: BarPeriod): void {
    if (chartRequest === null) {
      return;
    }
    const { instrument } = chartRequest;
    // The same page opens with the new bar period. The selected bar period keeps the focus.
    const instrumentPath = resolve('/instruments/[exchange]/[symbol]', {
      exchange: instrument.exchange,
      symbol: instrument.symbol,
    });
    const chartSearch = formatChartSearch({ instrument, barPeriod });
    // eslint-disable-next-line svelte/no-navigation-without-resolve -- resolve() made the path; only the search is added.
    void goto(`${instrumentPath}?${chartSearch}`, { replace: true, reset: false });
  }

  function describeBarCount(barCount: number): string {
    return barCount === 1 ? '1 bar' : `${String(barCount)} bars`;
  }
</script>

{#if chartRequest === null}
  <h1>Instrument not found</h1>
{:else}
  {@const instrumentName = formatInstrument(chartRequest.instrument)}
  <Workbench>
    <SideColumn label="Watchlist" side="start" width="20rem" storageKey="atrade.instrument-page.watchlist-column">
      <InstrumentWatchlist instrument={chartRequest.instrument} barPeriod={chartRequest.barPeriod} />
    </SideColumn>

    <PanelSplit storageKey="atrade.instrument-page.panel-split" panels={PANELS}>
      {#snippet panel(id, state)}
        {#if id === 'chart'}
          <Panel {...state} label={instrumentName}>
            {#snippet header()}
              <h1>{instrumentName}</h1>
              <span class="last-price" aria-label="Last price">{formatPrice(lastPrice)}</span>
              {#if shownDayQuote !== null}
                <ChangeText
                  value={shownDayQuote.change}
                  text={formatDayChange(shownDayQuote)}
                  label="Change from the previous close"
                />
              {/if}
              <div class="bar-periods">
                <ContentSwitcher
                  label="Bar period"
                  size="sm"
                  items={barPeriodItems}
                  value={chartRequest.barPeriod}
                  onValueChange={changeBarPeriod}
                />
              </div>
            {/snippet}
            <div class="chart">
              <div class="cds--visually-hidden">
                {#if barsResult?.kind === 'loaded'}
                  <span role="status" aria-label="Bar count">{describeBarCount(barsResult.bars.length)}</span>
                {/if}
                <span role="status" aria-label="Live bar">{liveBarText}</span>
              </div>
              <BarChart
                bars={chartBars}
                {liveBar}
                fill
                label="Bar chart of {instrumentName}, {chartRequest.barPeriod} bars"
              />
              {#if isLoading}
                <p class="chart-message" role="status">Loading bars.</p>
              {:else if barsResult?.kind === 'failed'}
                <p class="chart-message" role="alert"><StatusIndicator kind="error" label={barsResult.message} /></p>
              {:else if liveBarErrorText !== null}
                <p class="chart-message" role="alert"><StatusIndicator kind="error" label={liveBarErrorText} /></p>
              {/if}
            </div>
          </Panel>
        {:else}
          <Panel
            {...state}
            label="Paper account"
            tabs={{
              label: 'Paper account',
              items: accountTabItems,
              value: accountTable,
              onValueChange: (value: string) => {
                accountTable = value as AccountTable;
              },
            }}
          >
            <div class="account-table">
              <LiveUpdatesNotification isConnected={accountFeed.isConnected} />
              {#if accountTable === 'positions'}
                {#if account === null}
                  <p role="status">Reading the paper account.</p>
                {:else}
                  <PositionTable positions={account.positions} fill compact />
                {/if}
              {:else if accountTable === 'open-orders'}
                <OpenOrderList orders={accountFeed.openOrders} fill compact />
              {:else}
                <FilledManualOrderList orders={accountFeed.filledOrders} fill />
              {/if}
            </div>
          </Panel>
        {/if}
      {/snippet}
    </PanelSplit>

    <SideColumn label="Paper order" side="end" width="20rem" storageKey="atrade.instrument-page.order-column">
      <InstrumentOrderPanel
        isConnected={accountFeed.isConnected}
        instrument={chartRequest.instrument}
        {lastPrice}
        {account}
      />
    </SideColumn>
  </Workbench>
{/if}

<style>
  .last-price {
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }

  .bar-periods {
    flex: none;
    margin-inline-start: auto;
  }

  /* 6 short bar period names, each wide enough for its name. */
  .bar-periods :global(.cds--content-switcher) {
    inline-size: calc(var(--cds-spacing-10) * 5);
  }

  .bar-periods :global(.cds--content-switcher-btn) {
    justify-content: center;
    padding-inline: var(--cds-spacing-03);
  }

  /* The chart fills the panel body and follows its size (BarChart fill). */
  .chart {
    position: relative;
    flex: 1;
    min-block-size: 0;
    padding: var(--cds-spacing-03) var(--cds-spacing-05);
  }

  .chart-message {
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

  .account-table {
    display: flex;
    flex: 1;
    flex-direction: column;
    min-block-size: 0;
  }

  .account-table > :global(p),
  .account-table > :global(.open-orders > p) {
    margin: 0;
    padding: var(--cds-spacing-05);
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
    color: var(--cds-text-secondary);
  }
</style>
