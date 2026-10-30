<!-- The bar sources of a backtest in its source order, with the bar count of each bar source as a right-aligned
     tabular number (docs/architecture/backtest.md section 10.12). A backtest that did not finish has its source order
     but no bar counts. A backtest from before the source order has neither. -->
<script lang="ts">
  import { DataTable, type TableColumn } from '#lib/foundation/carbon';
  import { EmptyText } from '#lib/foundation/empty_text';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { MISSING_VALUE } from '#lib/foundation/value_format';
  import { formatBarSource, type BarSource } from '#lib/market_data';

  interface Props {
    sourceOrder: BarSource[] | null;
    barCountBySource: Record<string, number> | null;
  }

  const { sourceOrder, barCountBySource }: Props = $props();

  const COLUMNS: TableColumn[] = [{ header: 'Bar source' }, { header: 'Bars', align: 'right' }];
</script>

{#if sourceOrder === null}
  <EmptyText text="No bar sources" />
{:else}
  <ScrollRegion label="Bar sources" fill>
    <DataTable columns={COLUMNS} size="sm">
      {#snippet rows()}
        {#each sourceOrder as barSource (barSource)}
          <tr>
            <td>{formatBarSource(barSource)}</td>
            <td align="right">{barCountBySource?.[barSource] ?? MISSING_VALUE}</td>
          </tr>
        {/each}
      {/snippet}
    </DataTable>
  </ScrollRegion>
{/if}
