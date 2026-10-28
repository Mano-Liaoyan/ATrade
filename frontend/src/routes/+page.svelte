<!-- Home page: the instrument search adds to the watchlist, a watchlist instrument opens its instrument page, and the
     paper account panel shows the paper account. The running forward tests from /ws/forward-tests block paper orders
     by hand on their instruments. -->
<script lang="ts">
  import { ForwardTestsOnInstrumentsFeed } from '#lib/forward_test';
  import { InstrumentSearch, type Instrument } from '#lib/market_data';
  import { PaperAccountPanel } from '#lib/paper_trading';
  import {
    addToWatchlist,
    deleteFromWatchlist,
    listWatchlist,
    Watchlist,
    type WatchlistInstrument,
  } from '#lib/watchlist';
  import { createInstrumentHref } from './instrument_href';

  let watchlistInstruments: WatchlistInstrument[] = $state([]);
  let isWatchlistLoading = $state(true);
  let watchlistMessage: string | undefined = $state();

  const forwardTestsFeed = new ForwardTestsOnInstrumentsFeed();
  $effect(() => forwardTestsFeed.start(window.location));

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
</script>

<h1>ATrade</h1>
<div class="home-panels">
  <InstrumentSearch
    onSelect={(instrument: Instrument) => {
      void addInstrument(instrument);
    }}
    marker={(instrument: Instrument) => (isInWatchlist(instrument) ? 'In watchlist' : undefined)}
  />
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
<PaperAccountPanel blockingForwardTests={forwardTestsFeed.onInstruments} />

<style>
  .home-panels {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-start;
    gap: var(--cds-spacing-05);
  }

  .home-panels > :global(section) {
    flex: 1 1 22rem;
  }
</style>
