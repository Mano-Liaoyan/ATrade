<!-- Watchlist panel: a Carbon contained list. Each saved instrument is a link (the page decides the target) and has a
     Delete button. The page owns the list, so the instrument search on the same page can add to it. -->
<script lang="ts">
  import TrashCan16 from '@carbon/icons/es/trash-can/16.js';
  import WarningFilled16 from '@carbon/icons/es/warning--filled/16.js';
  import { Icon, Tooltip } from '#lib/foundation/carbon';
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

<section class="watchlist cds--contained-list cds--contained-list--on-page" aria-labelledby="watchlist-heading">
  <div class="cds--contained-list__header">
    <h2 id="watchlist-heading" class="cds--contained-list__label">Watchlist</h2>
  </div>
  {#if message !== undefined}
    <p class="watchlist-message watchlist-failed" role="alert"><Icon icon={WarningFilled16} />{message}</p>
  {/if}
  {#if isLoading}
    <p class="watchlist-message" role="status">Loading the watchlist.</p>
  {:else if instruments.length === 0}
    <p class="watchlist-message">The watchlist is empty.</p>
  {:else}
    <ScrollRegion label="Watchlist instruments" maxHeight="18rem">
      <ul class="watchlist-list">
        {#each instruments as instrument (instrument.id)}
          {@const instrumentName = formatWatchlistInstrument(instrument)}
          <li class="cds--contained-list-item cds--contained-list-item--with-action">
            <div class="cds--contained-list-item__content">
              <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- The page resolves the link in instrumentHref. -->
              <a class="instrument-link" href={instrumentHref(instrument)}>{instrumentName}</a>
            </div>
            <div class="cds--contained-list-item__action">
              <Tooltip text="Delete" align="left">
                {#snippet trigger({ props })}
                  <button
                    {...props}
                    type="button"
                    class="cds--btn cds--btn--ghost cds--btn--icon-only"
                    aria-label="Delete {instrumentName} from the watchlist"
                    onclick={() => {
                      onDelete(instrument);
                    }}
                  >
                    <Icon icon={TrashCan16} class="cds--btn__icon" />
                  </button>
                {/snippet}
              </Tooltip>
            </div>
          </li>
        {/each}
      </ul>
    </ScrollRegion>
  {/if}
</section>

<style>
  .watchlist {
    max-inline-size: 28rem;
  }

  /* The Carbon header row sets the type style. The heading inside takes it, not the browser size of h2. */
  .cds--contained-list__label {
    font: inherit;
    letter-spacing: inherit;
  }

  .watchlist-message {
    display: flex;
    align-items: center;
    gap: var(--cds-spacing-03);
    margin: 0;
    padding: var(--cds-spacing-03) var(--cds-spacing-05);
    color: var(--cds-text-secondary);
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
  }

  .watchlist-failed {
    color: var(--cds-text-error);
  }

  .watchlist-list {
    margin: 0;
    padding: 0;
  }

  /* Carbon has no link style in the loaded modules. The link uses the Carbon link tokens. */
  .instrument-link {
    color: var(--cds-link-primary);
    font-variant-numeric: tabular-nums;
    text-decoration: none;
  }

  .instrument-link:hover {
    color: var(--cds-link-primary-hover);
    text-decoration: underline;
  }
</style>
