<!-- The watchlist column of the instrument workbench: 32px rows with the symbol, the last price, and the change from
     the previous close (from the daily bars of each instrument). A row opens its instrument page with the same bar
     period. The open instrument is the selected row. -->
<script lang="ts">
  import { goto } from '$app/navigation';
  import { DataTable, type TableColumn } from '#lib/foundation/carbon';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { ChangeText, formatPrice, formatSignedNumber, MISSING_VALUE } from '#lib/foundation/value_format';
  import { readBars, readDayQuote, type BarPeriod, type DayQuote, type Instrument } from '#lib/market_data';
  import { listWatchlist, type WatchlistInstrument } from '#lib/watchlist';
  import { createInstrumentHref } from '../../../instrument_href';

  interface Props {
    instrument: Instrument;
    barPeriod: BarPeriod;
  }

  const { instrument, barPeriod }: Props = $props();

  const COLUMNS: TableColumn[] = [
    { header: 'Symbol' },
    { header: 'Last', align: 'right' },
    { header: 'Change', align: 'right' },
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

  function isOpen(watchlistInstrument: WatchlistInstrument): boolean {
    return (
      watchlistInstrument.symbol === instrument.symbol &&
      watchlistInstrument.exchange === instrument.exchange &&
      watchlistInstrument.currency === instrument.currency
    );
  }

  function formatChangePercent(quote: DayQuote | null | undefined): string {
    const changePercent = quote?.changePercent ?? null;
    return changePercent === null ? MISSING_VALUE : `${formatSignedNumber(changePercent)}%`;
  }

  // The link in the row is the keyboard way. A click anywhere in the row opens the same page.
  function openOnRowClick(href: string) {
    return (row: HTMLElement) => {
      const openInstrument = (event: MouseEvent): void => {
        if (!(event.target instanceof Element) || event.target.closest('a') === null) {
          // eslint-disable-next-line svelte/no-navigation-without-resolve -- createInstrumentHref resolved the path.
          void goto(href);
        }
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
    <ScrollRegion label="Watchlist" fill>
      <DataTable columns={COLUMNS} size="sm">
        {#snippet rows()}
          {#each watchlistInstruments as watchlistInstrument (watchlistInstrument.id)}
            {@const href = createInstrumentHref(watchlistInstrument, barPeriod)}
            {@const quote = quotes[watchlistInstrument.id]}
            <tr class={['row', isOpen(watchlistInstrument) && 'cds--data-table--selected']} {@attach openOnRowClick(href)}>
              <th scope="row">
                <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- createInstrumentHref resolved the path. -->
                <a class="symbol" {href} aria-current={isOpen(watchlistInstrument) ? 'page' : undefined}>
                  {watchlistInstrument.symbol}
                </a>
              </th>
              <td align="right">{formatPrice(quote?.last ?? null)}</td>
              <td align="right">
                <ChangeText value={quote?.changePercent ?? null} text={formatChangePercent(quote)} />
              </td>
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
    block-size: 100%;
    min-block-size: 0;
  }

  .row {
    cursor: pointer;
  }

  .row th {
    white-space: nowrap;
  }

  .symbol {
    color: var(--cds-text-primary);
    font-weight: var(--cds-heading-compact-01-font-weight);
    text-decoration: none;
  }

  .symbol:focus-visible {
    outline: 2px solid var(--cds-focus);
    outline-offset: -2px;
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
