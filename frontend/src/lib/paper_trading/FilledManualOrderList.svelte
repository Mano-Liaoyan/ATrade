<!-- Filled orders by hand: the stored order and its fills from IBKR (docs/architecture/paper_trading.md section 11.4). -->
<script lang="ts">
  import { DataTable, type TableColumn } from '#lib/foundation/carbon';
  import { formatUtcTime } from '#lib/foundation/time_format';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { formatAmount } from './paper_account';
  import type { ManualOrder } from './paper_orders';

  interface Props {
    orders: ManualOrder[];
  }

  const { orders }: Props = $props();

  const COLUMNS: TableColumn[] = [
    { header: 'Symbol' },
    { header: 'Side' },
    { header: 'Quantity', align: 'right' },
    { header: 'Filled', align: 'right' },
    { header: 'Average fill price', align: 'right' },
    { header: 'Type' },
    { header: 'Sent' },
  ];
</script>

{#if orders.length === 0}
  <p>No filled orders by hand today.</p>
{:else}
  <ScrollRegion label="Filled orders by hand" maxHeight="18rem">
    <DataTable columns={COLUMNS} size="sm">
      {#snippet rows()}
        {#each orders as order (order.id)}
          <tr>
            <th scope="row">{order.symbol} <span class="exchange">{order.exchange}</span></th>
            <td>{order.side}</td>
            <td align="right">{order.quantity}</td>
            <td align="right">{order.filled_quantity}</td>
            <td align="right">{formatAmount(order.average_fill_price)}</td>
            <td>{order.order_type} {order.time_in_force}</td>
            <td>{formatUtcTime(order.created_at_utc)}</td>
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

  .exchange {
    color: var(--cds-text-helper);
  }
</style>
