<!-- The Instruments tab of a multi-instrument backtest: one row for each universe member with its trade count, net
     profit, and the universe periods (quarters, or months of a monthly screen universe) as right-aligned tabular numbers (docs/architecture/backtest.md 10.10.7). It
     fills the height of its panel body and scrolls in itself. The forward test page uses it with the count header
     "Fills" (docs/architecture/forward_test.md 12.16). With `onRowSelect` (the backtest page, docs/architecture/
     indicator.md section 23.9.8), a click on a row or Enter selects the row, without a row number. -->
<script lang="ts">
  import { DataTable, SelectableTableRow, type TableColumn } from '#lib/foundation/carbon';
  import { EmptyText } from '#lib/foundation/empty_text';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import type { UniverseInstrument } from './backtest_api';
  import { formatUsd } from './backtest_format';

  interface Props {
    instruments: UniverseInstrument[];
    countHeader?: string;
    periodHeader?: string;
    selectedIndex?: number | null;
    onRowSelect?: (index: number) => void;
  }

  const { instruments, countHeader = 'Trades', periodHeader = 'Quarters', selectedIndex = null, onRowSelect }: Props = $props();

  const columns: TableColumn[] = $derived([
    { header: 'Instrument' },
    { header: countHeader, align: 'right' },
    { header: 'Net profit (USD)', align: 'right' },
    { header: periodHeader, align: 'right' },
  ]);
</script>

{#if instruments.length === 0}
  <EmptyText text="No instruments" />
{:else}
  <ScrollRegion label="Instruments" fill>
    <DataTable {columns} size="sm">
      {#snippet rows()}
        {#each instruments as instrument, instrumentIndex (`${instrument.symbol}:${instrument.exchange}`)}
          {#if onRowSelect === undefined}
            <tr>
              {@render cells(instrument)}
            </tr>
          {:else}
            <SelectableTableRow index={instrumentIndex} isSelected={instrumentIndex === selectedIndex} hasRowNumber={false} {onRowSelect}>
              {@render cells(instrument)}
            </SelectableTableRow>
          {/if}
        {/each}
      {/snippet}
    </DataTable>
  </ScrollRegion>
{/if}

{#snippet cells(instrument: UniverseInstrument)}
  <td>{instrument.symbol}</td>
  <td align="right">{instrument.trade_count}</td>
  <td align="right">{formatUsd(instrument.net_profit_usd)}</td>
  <td align="right">{instrument.quarter_count}</td>
{/snippet}
