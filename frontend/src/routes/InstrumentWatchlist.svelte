<!-- The watchlist column of a workbench (the home page and the instrument page): 32px rows with the symbol, the last
     price, and the change from the previous close (from the daily bars of each instrument). A row opens its
     instrument page, with the bar period of the open chart when there is one. On the instrument page, the open
     instrument is the selected row. With `editable` (the home page), the instrument search above the table adds an
     instrument, and each row has a Delete button. The side column around it is the "Watchlist" landmark, so this
     part has no landmark of its own. -->
<script lang="ts">
  import { goto } from '$app/navigation';
  import TrashCan16 from '@carbon/icons/es/trash-can/16.js';
  import { DataTable, IconButton, InlineNotification, type TableColumn } from '#lib/foundation/carbon';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { ChangeText, formatPrice, formatSignedNumber, MISSING_VALUE } from '#lib/foundation/value_format';
  import {
    InstrumentSearch,
    isSameInstrument,
    readBars,
    readDayQuote,
    type BarPeriod,
    type DayQuote,
    type Instrument,
  } from '#lib/market_data';
  import {
    addToWatchlist,
    deleteFromWatchlist,
    formatWatchlistInstrument,
    listWatchlist,
    type WatchlistInstrument,
  } from '#lib/watchlist';
  import { createInstrumentHref } from './instrument_href';

  interface Props {
    // The instrument of the open instrument page.
    instrument?: Instrument;
    // The bar period of the open chart. A row opens its instrument page with it.
    barPeriod?: BarPeriod;
    // The instrument search adds instruments, and each row has a Delete button (home page).
    editable?: boolean;
  }

  const { instrument, barPeriod, editable = false }: Props = $props();

  const COLUMNS: TableColumn[] = [
    { header: 'Symbol' },
    { header: 'Last', align: 'right' },
    { header: 'Change', align: 'right' },
  ];
  const EDITABLE_COLUMNS: TableColumn[] = [
    { header: 'Symbol' },
    { header: 'Last', align: 'right' },
    { header: 'Change', align: 'right' },
    { header: 'Delete', isMenu: true },
  ];

  // The number of daily bar requests at the same time.
  const QUOTE_READERS = 2;

  let instruments = $state<WatchlistInstrument[] | null>(null);
  let failedMessage = $state<string | null>(null);
  let changeMessage = $state<string | null>(null);
  let quotes = $state<Record<number, DayQuote | null>>({});
  let isMounted = true;
  // A function, so that the check after each await reads the current value.
  const isReading = (): boolean => isMounted;

  // Each daily bar request can call IBKR and save bars. A few requests at a time keep the backend free for the
  // chart, and the reads stop when the column leaves the page.
  function readQuotes(waiting: WatchlistInstrument[]): void {
    const readNextQuote = async (): Promise<void> => {
      for (let next = waiting.shift(); next !== undefined && isReading(); next = waiting.shift()) {
        const watchlistInstrument = next;
        const barsResult = await readBars(fetch, watchlistInstrument, '1-DAY');
        if (isReading()) {
          quotes[watchlistInstrument.id] = barsResult.kind === 'loaded' ? readDayQuote(barsResult.bars) : null;
        }
      }
    };
    for (let reader = 0; reader < QUOTE_READERS; reader += 1) {
      void readNextQuote();
    }
  }

  $effect(() => {
    isMounted = true;
    void listWatchlist(fetch).then((result) => {
      if (!isMounted) {
        return;
      }
      if (result.kind === 'failed') {
        failedMessage = result.message;
        return;
      }
      // Keep an instrument that the user added while the list loaded: the list can be older than the add.
      const listedIds = new Set(result.value.map((listed) => listed.id));
      const addedMeanwhile = (instruments ?? []).filter((added) => !listedIds.has(added.id));
      instruments = [...result.value, ...addedMeanwhile];
      readQuotes([...result.value]);
    });
    return () => {
      isMounted = false;
    };
  });

  function isOpen(watchlistInstrument: WatchlistInstrument): boolean {
    return instrument !== undefined && isSameInstrument(watchlistInstrument, instrument);
  }

  function isInWatchlist(candidate: Instrument): boolean {
    return (instruments ?? []).some((saved) => isSameInstrument(saved, candidate));
  }

  async function addInstrument(candidate: Instrument): Promise<void> {
    const addResult = await addToWatchlist(fetch, candidate);
    if (addResult.kind === 'ok') {
      instruments = [...(instruments ?? []), addResult.value];
      changeMessage = null;
      readQuotes([addResult.value]);
    } else {
      changeMessage = addResult.message;
    }
  }

  async function deleteInstrument(watchlistInstrument: WatchlistInstrument): Promise<void> {
    const deleteResult = await deleteFromWatchlist(fetch, watchlistInstrument.id);
    if (deleteResult.kind === 'ok') {
      instruments = (instruments ?? []).filter((saved) => saved.id !== watchlistInstrument.id);
      changeMessage = null;
    } else {
      changeMessage = deleteResult.message;
    }
  }

  function formatChangePercent(quote: DayQuote | null | undefined): string {
    const changePercent = quote?.changePercent ?? null;
    return changePercent === null ? MISSING_VALUE : `${formatSignedNumber(changePercent)}%`;
  }

  // The link in the row is the keyboard way. A click anywhere else in the row (not on a button) opens the same page.
  function openOnRowClick(href: string) {
    return (row: HTMLElement) => {
      const openInstrument = (event: MouseEvent): void => {
        if (!(event.target instanceof Element) || event.target.closest('a, button') === null) {
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

<div class="watchlist">
  {#if editable}
    <div class="search">
      <InstrumentSearch
        onSelect={(candidate: Instrument) => {
          void addInstrument(candidate);
        }}
        marker={(candidate: Instrument) => (isInWatchlist(candidate) ? 'In watchlist' : undefined)}
        placeholder="Add a symbol"
      />
    </div>
  {/if}
  {#if changeMessage !== null}
    <InlineNotification
      kind="error"
      title={changeMessage}
      lowContrast
      onClose={() => {
        changeMessage = null;
      }}
    />
  {/if}
  {#if failedMessage !== null}
    <p class="message message--error" role="alert">{failedMessage}</p>
  {:else if instruments === null}
    <p class="message" role="status">Loading the watchlist.</p>
  {:else if instruments.length === 0}
    <p class="message">No instruments in the watchlist.</p>
  {:else}
    {@const watchlistInstruments = instruments}
    <ScrollRegion label="Watchlist table" fill>
      <DataTable columns={editable ? EDITABLE_COLUMNS : COLUMNS} size="sm">
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
              {#if editable}
                <td class="cds--table-column-menu delete-cell">
                  <IconButton
                    label="Delete {formatWatchlistInstrument(watchlistInstrument)} from the watchlist"
                    icon={TrashCan16}
                    align="left"
                    onclick={() => {
                      void deleteInstrument(watchlistInstrument);
                    }}
                  />
                </td>
              {/if}
            </tr>
          {/each}
        {/snippet}
      </DataTable>
    </ScrollRegion>
  {/if}
</div>

<style>
  .watchlist {
    display: flex;
    flex-direction: column;
    block-size: 100%;
    min-block-size: 0;
  }

  .search {
    flex: none;
    padding: var(--cds-spacing-03) var(--cds-spacing-05);
  }

  .row {
    cursor: pointer;
  }

  .row th {
    white-space: nowrap;
  }

  /* The Delete button fills its cell above the 1px row border, so the row keeps the 32px height of the sm table. */
  .row td.delete-cell {
    inline-size: var(--cds-spacing-07);
    padding: 0;
  }

  .row td.delete-cell :global(.cds--btn) {
    block-size: calc(var(--cds-spacing-07) - 1px);
    min-block-size: 0;
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
