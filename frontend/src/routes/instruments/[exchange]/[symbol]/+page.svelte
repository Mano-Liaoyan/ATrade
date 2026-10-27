<!-- Instrument page: the bar chart of one instrument and one bar period. A watchlist instrument opens here.
     URL: /instruments/<exchange>/<symbol>?currency=<currency>&bar_period=<bar period>. -->
<script lang="ts">
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
  import {
    BAR_PERIODS,
    BarChart,
    formatChartSearch,
    formatInstrument,
    readBars,
    readChartRequest,
    type BarPeriod,
    type BarsResult,
  } from '#lib/market_data';

  const chartRequest = $derived(readChartRequest(page.params, page.url.searchParams));

  let barsResult: BarsResult | undefined = $state();
  let isLoading = $state(false);

  $effect(() => {
    if (chartRequest === null) {
      return;
    }
    const { instrument, barPeriod } = chartRequest;
    let isCurrent = true;
    isLoading = true;
    void readBars(fetch, instrument, barPeriod).then((result) => {
      if (isCurrent) {
        barsResult = result;
        isLoading = false;
      }
    });
    return () => {
      isCurrent = false;
    };
  });

  function changeBarPeriod(event: Event & { currentTarget: HTMLSelectElement }): void {
    if (chartRequest === null) {
      return;
    }
    const barPeriod = event.currentTarget.value as BarPeriod;
    const { instrument } = chartRequest;
    // The same page opens with the new bar period. The bar period list keeps the focus.
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
  <p>The page address must name the symbol, the exchange, and the currency.</p>
{:else}
  {@const instrumentName = formatInstrument(chartRequest.instrument)}
  <h1>{instrumentName}</h1>
  <form class="chart-controls" onsubmit={(event) => { event.preventDefault(); }}>
    <label for="bar-period">Bar period</label>
    <select id="bar-period" value={chartRequest.barPeriod} onchange={changeBarPeriod}>
      {#each BAR_PERIODS as barPeriod (barPeriod.value)}
        <option value={barPeriod.value}>{barPeriod.label}</option>
      {/each}
    </select>
    {#if isLoading}
      <span class="chart-message" role="status">Loading bars.</span>
    {:else if barsResult?.kind === 'failed'}
      <span class="chart-message chart-failed" role="alert">{barsResult.message}</span>
    {:else if barsResult?.kind === 'loaded'}
      <span class="chart-message" role="status" aria-label="Bar count">{describeBarCount(barsResult.bars.length)}</span>
    {/if}
  </form>
  <BarChart
    bars={barsResult?.kind === 'loaded' ? barsResult.bars : []}
    label="Bar chart of {instrumentName}, {chartRequest.barPeriod} bars"
  />
{/if}
<p><a href={resolve('/')}>Back to the watchlist</a></p>

<style>
  .chart-controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem 0.75rem;
    margin-bottom: 0.75rem;
  }

  .chart-message {
    color: var(--color-muted);
  }

  .chart-failed {
    color: var(--color-warning);
    font-weight: 600;
  }
</style>
