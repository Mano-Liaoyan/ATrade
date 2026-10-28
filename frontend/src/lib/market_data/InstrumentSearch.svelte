<!-- Instrument search: the user types a symbol, and the combo box shows each match as symbol / exchange / currency.
     ArrowUp and ArrowDown choose a match and Enter gives it to `onSelect`. A page can give `marker` to mark a match,
     for example "In watchlist". A marked match cannot be chosen. The search has no heading: the place around it (the
     watchlist column of the home page) names it. The field is the 32px size of the workbench lines. -->
<script lang="ts">
  import { Combobox, Tag, type ComboboxItem } from '#lib/foundation/carbon';
  import { formatInstrument, searchInstruments, type Instrument, type InstrumentSearchResult } from './instrument_search';

  const {
    onSelect,
    marker,
  }: {
    onSelect: (instrument: Instrument) => void;
    marker?: (instrument: Instrument) => string | undefined;
  } = $props();

  // IBKR allows about 1 symbol search per second, so the search waits until the user stops typing.
  const TYPING_PAUSE_MILLISECONDS = 500;

  let searchedQuery = $state('');
  let isSearching = $state(false);
  let searchResult: InstrumentSearchResult | undefined = $state();
  let searchTimer: ReturnType<typeof setTimeout> | undefined;
  let latestSearchNumber = 0;

  const instruments = $derived(searchResult?.kind === 'found' ? searchResult.instruments : []);
  const items: ComboboxItem[] = $derived(
    instruments.map((instrument) => ({
      value: formatInstrument(instrument),
      label: formatInstrument(instrument),
      disabled: marker?.(instrument) !== undefined,
    })),
  );
  const statusText = $derived.by(() => {
    if (isSearching) {
      return 'Searching.';
    }
    if (searchResult?.kind === 'found' && searchResult.instruments.length === 0) {
      return `No instrument matches "${searchedQuery}".`;
    }
    return undefined;
  });

  async function search(query: string): Promise<void> {
    latestSearchNumber += 1;
    const searchNumber = latestSearchNumber;
    isSearching = true;
    const result = await searchInstruments(fetch, query);
    // An older answer must not replace the answer for newer text.
    if (searchNumber !== latestSearchNumber) {
      return;
    }
    searchResult = result;
    searchedQuery = query;
    isSearching = false;
  }

  function scheduleSearch(text: string): void {
    clearTimeout(searchTimer);
    const query = text.trim();
    if (query === '') {
      latestSearchNumber += 1;
      searchResult = undefined;
      isSearching = false;
      return;
    }
    searchTimer = setTimeout(() => {
      void search(query);
    }, TYPING_PAUSE_MILLISECONDS);
  }

  function selectInstrument(value: string): void {
    const instrument = instruments.find((candidate) => formatInstrument(candidate) === value);
    if (instrument !== undefined) {
      onSelect(instrument);
    }
  }

  $effect(() => {
    return () => {
      clearTimeout(searchTimer);
    };
  });
</script>

{#snippet candidateMarker(item: ComboboxItem)}
  {@const instrument = instruments.find((candidate) => formatInstrument(candidate) === item.value)}
  {@const markerText = instrument === undefined ? undefined : marker?.(instrument)}
  {#if markerText !== undefined}
    <Tag label={markerText} size="sm" />
  {/if}
{/snippet}

<div class="instrument-search" role="search" aria-label="Instrument search">
  <Combobox
    label="Symbol"
    hideLabel
    size="sm"
    placeholder="Add a symbol"
    {items}
    listLabel="Instrument search results"
    onInput={scheduleSearch}
    onSelect={selectInstrument}
    {statusText}
    invalidText={searchResult?.kind === 'failed' ? searchResult.message : undefined}
    itemContent={candidateMarker}
  />
</div>

