<!-- PROTOTYPE (#99), throwaway: the watchlist column of the instrument workbench. A row opens its instrument page
     with the same bar period. The last price comes from the 1-DAY bars of each instrument. -->
<script lang="ts">
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { DataTable, type TableColumn } from '#lib/foundation/carbon';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { formatChartSearch, readBars, type BarPeriod, type Instrument } from '#lib/market_data';
  import { listWatchlist, type WatchlistInstrument } from '#lib/watchlist';
  import { formatPrice, readDayQuote, type DayQuote } from './instrument_quote';

  interface Props {
    instrument: Instrument;
    barPeriod: BarPeriod;
  }

  const { instrument, barPeriod }: Props = $props();

  const COLUMNS: TableColumn[] = [
    { header: 'Symbol' },
    { header: 'Exchange' },
    { header: 'Last', align: 'right' },
  ];

  let instruments = $state<WatchlistInstrument[] | null>(null);
  let failedMessage = $state<string | null>(null);
  let quotes = $state<Record<number, DayQuote | null>>({});

  $effect(() => {
    let isCurrent = true;
    void listWatchlist(fetch).then((result) => {
      if (!isCurrent) {
        return;
      }
      if (result.kind === 'failed') {
        failedMessage = result.message;
        return;
      }
      instruments = result.value;
      for (const watchlistInstrument of result.value) {
        void readBars(fetch, watchlistInstrument, '1-DAY').then((barsResult) => {
          if (isCurrent) {
            quotes[watchlistInstrument.id] = barsResult.kind === 'loaded' ? readDayQuote(barsResult.bars) : null;
          }
        });
      }
    });
    return () => {
      isCurrent = false;
    };
  });

  function instrumentHref(watchlistInstrument: WatchlistInstrument): string {
    const path = resolve('/instruments/[exchange]/[symbol]', {
      exchange: watchlistInstrument.exchange,
      symbol: watchlistInstrument.symbol,
    });
    return `${path}?${formatChartSearch({ instrument: watchlistInstrument, barPeriod })}`;
  }

  function isOpen(watchlistInstrument: WatchlistInstrument): boolean {
    return (
      watchlistInstrument.symbol === instrument.symbol &&
      watchlistInstrument.exchange === instrument.exchange &&
      watchlistInstrument.currency === instrument.currency
    );
  }

  // The link in the row is the keyboard path. A click anywhere in the row opens the same page.
  function openOnRowClick(href: string) {
    return (row: HTMLElement) => {
      const openInstrument = (event: MouseEvent): void => {
        if (event.target instanceof HTMLAnchorElement) {
          return;
        }
        // eslint-disable-next-line svelte/no-navigation-without-resolve -- instrumentHref resolved the path.
        void goto(href);
      };
      row.addEventListener('click', openInstrument);
      return () => {
        row.removeEventListener('click', openInstrument);
      };
    };
  }
</script>

<nav class="watchlist" aria-label="Watchlist">
  {#if failedMessage !== null}
    <p class="message message--error" role="alert">{failedMessage}</p>
  {:else if instruments === null}
    <p class="message" role="status">Loading the watchlist.</p>
  {:else if instruments.length === 0}
    <p class="message">No instruments in the watchlist.</p>
  {:else}
    {@const watchlistInstruments = instruments}
    <ScrollRegion label="Watchlist" maxHeight="100%">
      <DataTable columns={COLUMNS} size="sm">
        {#snippet rows()}
          {#each watchlistInstruments as watchlistInstrument (watchlistInstrument.id)}
            {@const href = instrumentHref(watchlistInstrument)}
            {@const quote = quotes[watchlistInstrument.id]}
            <tr
              class={['row', isOpen(watchlistInstrument) && 'cds--data-table--selected']}
              {@attach openOnRowClick(href)}
            >
              <th scope="row">
                <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- instrumentHref resolved the path. -->
                <a class="symbol" {href} aria-current={isOpen(watchlistInstrument) ? 'page' : undefined}>
                  {watchlistInstrument.symbol}
                </a>
              </th>
              <td class="exchange">{watchlistInstrument.exchange}</td>
              <td align="right">{formatPrice(quote?.last ?? null)}</td>
            </tr>
          {/each}
        {/snippet}
      </DataTable>
    </ScrollRegion>
  {/if}
</nav>

<style>
  .watchlist {
    display: flex;
    flex-direction: column;
    min-block-size: 0;
    block-size: 100%;
  }

  .watchlist :global(.scroll-region) {
    block-size: 100%;
  }

  .row {
    cursor: pointer;
  }

  .symbol {
    color: var(--cds-text-primary);
    text-decoration: none;
    font-weight: var(--cds-heading-compact-01-font-weight);
  }

  .symbol:focus-visible {
    outline: 2px solid var(--cds-focus);
    outline-offset: -2px;
  }

  .exchange {
    color: var(--cds-text-secondary);
  }

  .message {
    margin: 0;
    padding: var(--cds-spacing-05);
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
    letter-spacing: var(--cds-body-compact-01-letter-spacing);
    color: var(--cds-text-secondary);
  }

  .message--error {
    color: var(--cds-text-error);
  }
</style>
