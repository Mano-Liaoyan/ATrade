<!-- Instrument search panel: the user types a symbol, and the panel lists each match as symbol / exchange / currency.
     A page can give `resultAction` to show a control next to each result, for example "Add to watchlist". -->
<script lang="ts">
  import type { Snippet } from 'svelte';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { formatInstrument, searchInstruments, type Instrument, type InstrumentSearchResult } from './instrument_search';

  const { resultAction }: { resultAction?: Snippet<[Instrument]> } = $props();

  let query = $state('');
  let searchedQuery = $state('');
  let isSearching = $state(false);
  let searchResult: InstrumentSearchResult | undefined = $state();

  async function submitSearch(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    const trimmedQuery = query.trim();
    if (trimmedQuery === '') {
      return;
    }
    // A form submit sends one request. IBKR allows about 1 symbol search per second.
    isSearching = true;
    searchResult = await searchInstruments(fetch, trimmedQuery);
    searchedQuery = trimmedQuery;
    isSearching = false;
  }
</script>

<section class="instrument-search" aria-labelledby="instrument-search-heading">
  <h2 id="instrument-search-heading">Instrument search</h2>
  <form class="search-form" role="search" onsubmit={submitSearch}>
    <label for="instrument-search-query">Symbol</label>
    <input id="instrument-search-query" type="search" autocomplete="off" placeholder="AAPL or 700" bind:value={query} />
    <button type="submit" disabled={isSearching}>Search</button>
  </form>
  {#if isSearching}
    <p class="search-message" role="status">Searching.</p>
  {:else if searchResult?.kind === 'failed'}
    <p class="search-message search-failed" role="alert">{searchResult.message}</p>
  {:else if searchResult?.kind === 'found' && searchResult.instruments.length === 0}
    <p class="search-message" role="status">No instrument matches "{searchedQuery}".</p>
  {:else if searchResult?.kind === 'found'}
    <ScrollRegion label="Instrument search results" maxHeight="18rem">
      <ul class="result-list">
        {#each searchResult.instruments as instrument (formatInstrument(instrument))}
          <li class="result-item">
            <span class="result-name">{formatInstrument(instrument)}</span>
            {@render resultAction?.(instrument)}
          </li>
        {/each}
      </ul>
    </ScrollRegion>
  {/if}
</section>

<style>
  .instrument-search {
    max-width: 28rem;
    padding: 1rem;
    border: 1px solid var(--color-border);
    border-radius: 0.5rem;
    background: var(--color-surface);
  }

  h2 {
    margin: 0 0 0.75rem;
    font-size: 1rem;
  }

  .search-form {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
  }

  .search-form input {
    flex: 1;
    min-width: 0;
  }

  .search-message {
    margin: 0;
    color: var(--color-muted);
  }

  .search-failed {
    color: var(--color-warning);
    font-weight: 600;
  }

  .result-list {
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .result-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    padding: 0.375rem 0.5rem;
    border-bottom: 1px solid var(--color-border);
    font-variant-numeric: tabular-nums;
  }
</style>
