<!-- The recorded fills of one forward test (docs/architecture/forward_test.md section 12.8), oldest first: the Fills tab
     of the forward test page. The columns are the columns of the Trades tab of the backtest page, and the amount. A stock
     split adjustment is a row too (section 12.16): "Split 4:1" in Side, the change of the share count, no price, and
     the cash in lieu as the amount. -->
<script lang="ts">
  import { DataTable, type TableColumn } from '#lib/foundation/carbon';
  import { EmptyText } from '#lib/foundation/empty_text';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { formatUtcTime } from '#lib/foundation/time_format';
  import { formatAmount, formatSplitRatio } from '#lib/foundation/value_format';
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
    { header: 'Amount (USD)', align: 'right' },
  ];

  function describeSide(fill: ForwardTestFill): string {
    return fill.kind === 'split_adjustment' ? `Split ${formatSplitRatio(fill.split_ratio ?? '1')}` : fill.side;
  }

  function describeQuantity(fill: ForwardTestFill): string {
    if (fill.kind === 'fill') {
      return fill.quantity_shares;
    }
    return fill.side === 'BUY' ? `+${fill.quantity_shares}` : `−${fill.quantity_shares}`;
  }
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
            <td>{describeSide(fill)}</td>
            <td align="right">{describeQuantity(fill)}</td>
            <td align="right">{fill.price_usd === null ? '' : formatAmount(fill.price_usd)}</td>
            <td align="right">{fill.kind === 'fill' ? formatAmount(fill.commission_usd) : ''}</td>
            <td align="right">{formatAmount(fill.amount_usd)}</td>
          </tr>
        {/each}
      {/snippet}
    </DataTable>
  </ScrollRegion>
{/if}
