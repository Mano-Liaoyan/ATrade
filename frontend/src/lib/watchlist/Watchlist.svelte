<!-- Watchlist panel: each saved instrument is a link (the page decides the target) and has a Delete button.
     The page owns the list, so the instrument search on the same page can add to it. -->
<script lang="ts">
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { formatWatchlistInstrument, type WatchlistInstrument } from './watchlist_api';

  const {
    instruments,
    isLoading,
    message,
    instrumentHref,
    onDelete,
  }: {
    instruments: WatchlistInstrument[];
    isLoading: boolean;
    message: string | undefined;
    instrumentHref: (instrument: WatchlistInstrument) => string;
    onDelete: (instrument: WatchlistInstrument) => void;
  } = $props();
</script>

<section class="watchlist" aria-labelledby="watchlist-heading">
  <h2 id="watchlist-heading">Watchlist</h2>
  {#if message !== undefined}
    <p class="watchlist-message watchlist-failed" role="alert">{message}</p>
  {/if}
  {#if isLoading}
    <p class="watchlist-message" role="status">Loading the watchlist.</p>
  {:else if instruments.length === 0}
    <p class="watchlist-message">The watchlist is empty. Add instruments from the instrument search.</p>
  {:else}
    <ScrollRegion label="Watchlist instruments" maxHeight="18rem">
      <ul class="watchlist-list">
        {#each instruments as instrument (instrument.id)}
          <li class="watchlist-item">
            <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- The page resolves the link in instrumentHref. -->
            <a href={instrumentHref(instrument)}>{formatWatchlistInstrument(instrument)}</a>
            <button
              type="button"
              aria-label="Delete {formatWatchlistInstrument(instrument)} from the watchlist"
              onclick={() => {
                onDelete(instrument);
              }}>Delete</button
            >
          </li>
        {/each}
      </ul>
    </ScrollRegion>
  {/if}
</section>

<style>
  .watchlist {
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

  .watchlist-message {
    margin: 0 0 0.5rem;
    color: var(--color-muted);
  }

  .watchlist-failed {
    color: var(--color-warning);
    font-weight: 600;
  }

  .watchlist-list {
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .watchlist-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    padding: 0.375rem 0.5rem;
    border-bottom: 1px solid var(--color-border);
    font-variant-numeric: tabular-nums;
  }
</style>
