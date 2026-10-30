<!-- The HK instrument list editor (market_data.md section 8.10): the user pastes symbols, sees the result of each
     symbol (added, not found, already in list), and deletes a row. The table scrolls in its own ScrollRegion. -->
<script lang="ts">
  import TrashCan16 from '@carbon/icons/es/trash-can/16.js';
  import {
    Button,
    DataTable,
    IconButton,
    InlineNotification,
    StatusIndicator,
    TextInput,
    type StatusKind,
    type TableColumn,
  } from '#lib/foundation/carbon';
  import { EmptyText } from '#lib/foundation/empty_text';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { formatUtcTime } from '#lib/foundation/time_format';
  import {
    addToHkInstrumentList,
    deleteFromHkInstrumentList,
    listHkInstrumentList,
    splitPastedSymbols,
    type HkInstrument,
    type HkInstrumentsAdded,
  } from './hk_instrument_list';

  interface SymbolResult {
    symbol: string;
    kind: StatusKind;
    label: string;
  }

  const COLUMNS: TableColumn[] = [{ header: 'Symbol' }, { header: 'Added' }, { header: 'Delete', isMenu: true }];

  let instruments = $state<HkInstrument[] | null>(null);
  let readFailedMessage = $state<string | null>(null);
  let changeMessage = $state<string | null>(null);
  let pastedText = $state('');
  let invalidText = $state<string | null>(null);
  let isAdding = $state(false);
  let symbolResults = $state<SymbolResult[]>([]);
  let deletingIds = $state<number[]>([]);

  async function readInstruments(): Promise<void> {
    const listResult = await listHkInstrumentList(fetch);
    if (listResult.kind === 'failed') {
      readFailedMessage = listResult.message;
      return;
    }
    readFailedMessage = null;
    instruments = listResult.value;
  }

  $effect(() => {
    void readInstruments();
  });

  function toSymbolResults(added: HkInstrumentsAdded): SymbolResult[] {
    return [
      ...added.added.map((symbol) => ({ symbol, kind: 'success' as const, label: `${symbol} added` })),
      ...added.not_found.map((symbol) => ({ symbol, kind: 'error' as const, label: `${symbol} not found` })),
      ...added.already_in_list.map((symbol) => ({
        symbol,
        kind: 'warning' as const,
        label: `${symbol} already in list`,
      })),
    ];
  }

  async function addPastedSymbols(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    const symbols = splitPastedSymbols(pastedText);
    if (symbols.length === 0) {
      invalidText = 'Paste at least 1 symbol.';
      return;
    }
    invalidText = null;
    isAdding = true;
    const addResult = await addToHkInstrumentList(fetch, symbols);
    isAdding = false;
    if (addResult.kind === 'failed') {
      changeMessage = addResult.message;
      return;
    }
    changeMessage = null;
    symbolResults = toSymbolResults(addResult.value);
    pastedText = '';
    await readInstruments();
  }

  async function deleteInstrument(instrument: HkInstrument): Promise<void> {
    deletingIds = [...deletingIds, instrument.id];
    const deleteResult = await deleteFromHkInstrumentList(fetch, instrument.id);
    deletingIds = deletingIds.filter((deletingId) => deletingId !== instrument.id);
    if (deleteResult.kind === 'failed') {
      changeMessage = deleteResult.message;
      return;
    }
    changeMessage = null;
    instruments = (instruments ?? []).filter((listed) => listed.id !== instrument.id);
  }
</script>

<div class="editor">
  <form
    class="add-form"
    onsubmit={(event) => {
      void addPastedSymbols(event);
    }}
  >
    <TextInput label="Symbols" bind:value={pastedText} {invalidText} autocomplete="off" />
    <Button type="submit" size="md" disabled={isAdding}>
      {isAdding ? 'Checking…' : 'Add to HK instrument list'}
    </Button>
  </form>
  {#if symbolResults.length > 0}
    <ul class="results" aria-label="Add results">
      {#each symbolResults as symbolResult, index (index)}
        <li><StatusIndicator kind={symbolResult.kind} label={symbolResult.label} /></li>
      {/each}
    </ul>
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
  {#if readFailedMessage !== null}
    <InlineNotification kind="error" title="HK instrument list not read" subtitle={readFailedMessage} lowContrast />
  {:else if instruments === null}
    <EmptyText text="Loading" role="status" />
  {:else if instruments.length === 0}
    <EmptyText text="No instruments" />
  {:else}
    {@const listedInstruments = instruments}
    <ScrollRegion label="HK instrument list table" maxHeight="24rem">
      <DataTable columns={COLUMNS} size="sm">
        {#snippet rows()}
          {#each listedInstruments as instrument (instrument.id)}
            <tr>
              <th scope="row">{instrument.symbol}</th>
              <td class="time">{formatUtcTime(instrument.added_at_utc)}</td>
              <td class="cds--table-column-menu delete-cell">
                {@const isDeleting = deletingIds.includes(instrument.id)}
                <IconButton
                  label={isDeleting
                    ? `Deleting ${instrument.symbol} from the HK instrument list`
                    : `Delete ${instrument.symbol} from the HK instrument list`}
                  icon={TrashCan16}
                  align="left"
                  disabled={isDeleting}
                  busy={isDeleting}
                  onclick={() => {
                    void deleteInstrument(instrument);
                  }}
                />
              </td>
            </tr>
          {/each}
        {/snippet}
      </DataTable>
    </ScrollRegion>
  {/if}
</div>

<style>
  .editor {
    display: flex;
    flex-direction: column;
    gap: var(--cds-spacing-05);
    max-inline-size: 40rem;
  }

  .add-form {
    display: flex;
    align-items: flex-end;
    gap: var(--cds-spacing-05);
  }

  .add-form :global(.cds--form-item) {
    flex: 1;
  }

  .results {
    display: flex;
    flex-wrap: wrap;
    gap: var(--cds-spacing-03) var(--cds-spacing-06);
  }

  .time {
    font-variant-numeric: tabular-nums;
  }

  /* The Delete button fills its cell above the 1px row border, so the row keeps the 32px height of the sm table. */
  .delete-cell {
    inline-size: var(--cds-spacing-07);
    padding: 0;
  }

  .delete-cell :global(.cds--btn) {
    block-size: calc(var(--cds-spacing-07) - 1px);
    min-block-size: 0;
  }
</style>
