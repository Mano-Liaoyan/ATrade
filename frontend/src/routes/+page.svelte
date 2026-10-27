<!-- Home page: the instrument search adds to the watchlist, a watchlist instrument opens its instrument page, and the
     paper account panel shows the paper account. -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import { InstrumentSearch, type Instrument } from '#lib/market_data';
  import { PaperAccountPanel } from '#lib/paper_trading';
  import {
    addToWatchlist,
    deleteFromWatchlist,
    formatWatchlistInstrument,
    listWatchlist,
    Watchlist,
    type WatchlistInstrument,
  } from '#lib/watchlist';

  let watchlistInstruments: WatchlistInstrument[] = $state([]);
  let isWatchlistLoading = $state(true);
  let watchlistMessage: string | undefined = $state();

  $effect(() => {
    void listWatchlist(fetch).then((listResult) => {
      if (listResult.kind === 'ok') {
        // Keep an instrument that the user added while the list loaded: the list can be older than the add.
        const listedIds = new Set(listResult.value.map((listed) => listed.id));
        const addedMeanwhile = watchlistInstruments.filter((added) => !listedIds.has(added.id));
        watchlistInstruments = [...listResult.value, ...addedMeanwhile];
      } else {
        watchlistMessage = listResult.message;
      }
      isWatchlistLoading = false;
    });
  });

  function isInWatchlist(instrument: Instrument): boolean {
    return watchlistInstruments.some(
      (saved) =>
        saved.symbol === instrument.symbol &&
        saved.exchange === instrument.exchange &&
        saved.currency === instrument.currency,
    );
  }

  async function addInstrument(instrument: Instrument): Promise<void> {
    const addResult = await addToWatchlist(fetch, instrument);
    if (addResult.kind === 'ok') {
      watchlistInstruments = [...watchlistInstruments, addResult.value];
      watchlistMessage = undefined;
    } else {
      watchlistMessage = addResult.message;
    }
  }

  async function deleteInstrument(instrument: WatchlistInstrument): Promise<void> {
    const deleteResult = await deleteFromWatchlist(fetch, instrument.id);
    if (deleteResult.kind === 'ok') {
      watchlistInstruments = watchlistInstruments.filter((saved) => saved.id !== instrument.id);
      watchlistMessage = undefined;
    } else {
      watchlistMessage = deleteResult.message;
    }
  }

  function createInstrumentHref(instrument: WatchlistInstrument): string {
    const instrumentPath = resolve('/instruments/[exchange]/[symbol]', {
      exchange: instrument.exchange,
      symbol: instrument.symbol,
    });
    const searchParameters = new URLSearchParams({ currency: instrument.currency });
    return `${instrumentPath}?${searchParameters.toString()}`;
  }
</script>

{#snippet addToWatchlistButton(instrument: Instrument)}
  {#if isInWatchlist(instrument)}
    <span class="in-watchlist">In watchlist</span>
  {:else}
    <button
      type="button"
      aria-label="Add {formatWatchlistInstrument(instrument)} to the watchlist"
      onclick={() => {
        void addInstrument(instrument);
      }}>Add</button
    >
  {/if}
{/snippet}

<h1>ATrade</h1>
<div class="home-panels">
  <InstrumentSearch resultAction={addToWatchlistButton} />
  <Watchlist
    instruments={watchlistInstruments}
    isLoading={isWatchlistLoading}
    message={watchlistMessage}
    instrumentHref={createInstrumentHref}
    onDelete={(instrument: WatchlistInstrument) => {
      void deleteInstrument(instrument);
    }}
  />
</div>
<PaperAccountPanel />

<style>
  .home-panels {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-start;
    gap: 1rem;
  }

  .home-panels > :global(section) {
    flex: 1 1 22rem;
  }

  .in-watchlist {
    color: var(--color-muted);
    font-size: 0.875rem;
  }
</style>
