<!-- The recorded fills of one forward test (docs/architecture/forward_test.md section 12.8), oldest first. -->
<script lang="ts">
  import { DataTable, type TableColumn } from '#lib/foundation/carbon';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { formatUtcTime } from '#lib/foundation/time_format';
  import { formatAmount } from '#lib/foundation/value_format';
  import type { ForwardTestFill } from './forward_test_api';

  const { fills }: { fills: ForwardTestFill[] } = $props();

  const COLUMNS: TableColumn[] = [
    { header: 'Time' },
    { header: 'Side' },
    { header: 'Quantity', align: 'right' },
    { header: 'Price (USD)', align: 'right' },
    { header: 'Commission (USD)', align: 'right' },
  ];
</script>

{#if fills.length === 0}
  <p>No fill yet.</p>
{:else}
  <ScrollRegion label="Forward test fills" maxHeight="min(20rem, 45vh)">
    <DataTable columns={COLUMNS} size="sm">
      {#snippet rows()}
        {#each fills as fill, fillIndex (fillIndex)}
          <tr>
            <th scope="row">{formatUtcTime(fill.time_utc)}</th>
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

<style>
  p {
    margin: 0;
  }
</style>
