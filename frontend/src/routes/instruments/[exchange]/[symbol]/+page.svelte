<!-- Instrument page: the bar chart of one instrument and one bar period, with live bars from /ws/market-data.
     A watchlist instrument opens here.
     URL: /instruments/<exchange>/<symbol>?currency=<currency>&bar_period=<bar period>. -->
<script lang="ts">
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
  import { Tabs } from '#lib/foundation/carbon';
  import { buildSocketUrl, openLiveSocket } from '#lib/foundation/live_socket';
  import { readPrototypeVariant } from '#lib/foundation/prototype_switcher';
  import {
    BAR_PERIODS,
    BarChart,
    describeLiveBar,
    formatChartSearch,
    formatInstrument,
    formatLiveBarsPath,
    readBars,
    readChartRequest,
    readLiveBarMessage,
    type Bar,
    type BarPeriod,
    type BarsResult,
  } from '#lib/market_data';
  import InstrumentWorkbenchPrototype from './InstrumentWorkbenchPrototype.svelte';

  // PROTOTYPE (#99), throwaway: "current" shows the PR #98 page, "workbench" the 3-column workbench.
  const prototypeVariant = $derived(readPrototypeVariant(new URLSearchParams(page.url.search)));

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

  const liveBarText = $derived.by(() => {
    if (liveBarError !== null) {
      return `No live bars. ${liveBarError}`;
    }
    if (liveBar !== null) {
      return describeLiveBar(liveBar);
    }
    return isLiveSocketConnected ? 'Waiting for live bars.' : 'Connecting to live bars.';
  });

  function changeBarPeriod(value: string): void {
    if (chartRequest === null) {
      return;
    }
    const barPeriod = value as BarPeriod;
    const { instrument } = chartRequest;
    // The same page opens with the new bar period. The selected tab keeps the focus.
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

{#if prototypeVariant === 'workbench' && chartRequest !== null}
  <InstrumentWorkbenchPrototype
    {chartRequest}
    bars={chartBars}
    {liveBar}
    {isLoading}
    barsError={barsResult?.kind === 'failed' ? barsResult.message : null}
    {liveBarError}
    onBarPeriodChange={changeBarPeriod}
  />
{:else}
{#if chartRequest === null}
  <h1>Instrument not found</h1>
{:else}
  {@const instrumentName = formatInstrument(chartRequest.instrument)}
  <h1>{instrumentName}</h1>
  <Tabs label="Bar period" items={BAR_PERIODS} value={chartRequest.barPeriod} onValueChange={changeBarPeriod}>
    {#snippet panel()}
      <div class="chart-status">
        {#if isLoading}
          <span role="status">Loading bars.</span>
        {:else if barsResult?.kind === 'failed'}
          <span class="chart-failed" role="alert">{barsResult.message}</span>
        {:else if barsResult?.kind === 'loaded'}
          <span role="status" aria-label="Bar count">{describeBarCount(barsResult.bars.length)}</span>
        {/if}
        <span class:chart-failed={liveBarError !== null} role="status" aria-label="Live bar">{liveBarText}</span>
      </div>
      <BarChart
        bars={chartBars}
        {liveBar}
        label="Bar chart of {instrumentName}, {chartRequest.barPeriod} bars"
      />
    {/snippet}
  </Tabs>
{/if}
<p class="instrument-back"><a class="cds--link" href={resolve('/')}>Back to the watchlist</a></p>
{/if}

<style>
  .chart-status {
    display: flex;
    flex-wrap: wrap;
    gap: var(--cds-spacing-03) var(--cds-spacing-06);
    margin-block-end: var(--cds-spacing-05);
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
    letter-spacing: var(--cds-body-compact-01-letter-spacing);
    color: var(--cds-text-secondary);
    font-variant-numeric: tabular-nums;
  }

  .chart-failed {
    color: var(--cds-text-error);
  }

  .instrument-back {
    margin-block: 0;
  }
</style>
