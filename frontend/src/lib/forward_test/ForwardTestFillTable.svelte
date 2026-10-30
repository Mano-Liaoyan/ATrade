<!-- The recorded fills of one forward test (docs/architecture/forward_test.md section 12.8), oldest first: the Fills tab
     of the forward test page. The columns are the columns of the Trades tab of the backtest page. -->
<script lang="ts">
  import { DataTable, type TableColumn } from '#lib/foundation/carbon';
  import { EmptyText } from '#lib/foundation/empty_text';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { formatUtcTime } from '#lib/foundation/time_format';
  import { formatAmount } from '#lib/foundation/value_format';
  import type { ForwardTestFill } from './forward_test_api';

  const { fills }: { fills: ForwardTestFill[] } = $props();

  const COLUMNS: TableColumn[] = [
    { header: '#', align: 'right' },
    { header: 'Time' },
    { header: 'Symbol' },
    { header: 'Side' },
    { header: 'Quantity', align: 'right' },
    { header: 'Price (USD)', align: 'right' },
    { header: 'Commission (USD)', align: 'right' },
  ];
</script>

{#if fills.length === 0}
  <EmptyText text="No fills" />
{:else}
  <ScrollRegion label="Fills" fill>
    <DataTable columns={COLUMNS} size="sm">
      {#snippet rows()}
        {#each fills as fill, fillIndex (fillIndex)}
          <tr>
            <th scope="row" align="right">{fillIndex + 1}</th>
            <td>{formatUtcTime(fill.time_utc)}</td>
            <td>{fill.symbol}</td>
            <td>{fill.side}</td>
            <td align="right">{fill.quantity_shares}</td>
            <td align="right">{formatAmount(fill.price_usd)}</td>
            <td align="right">{formatAmount(fill.commission_usd)}</td>
          </tr>
        {/each}
      {/snippet}
    </DataTable>
  </ScrollRegion>
{/if}
