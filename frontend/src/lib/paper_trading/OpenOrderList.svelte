<!-- Open orders of the paper account from IBKR, with the source of each order. The row menu cancels an order by hand.
     For other orders, the cancel item is disabled and says why. -->
<script lang="ts">
  import { DataTable, InlineNotification, OverflowMenu, type TableColumn } from '#lib/foundation/carbon';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { formatAmount } from './paper_account';
  import { cancelPaperOrder, describeCancelAction, describeOrderSource, type OpenOrder } from './paper_orders';

  interface Props {
    orders: OpenOrder[];
  }

  const { orders }: Props = $props();

  const COLUMNS: TableColumn[] = [
    { header: 'Symbol' },
    { header: 'Side' },
    { header: 'Quantity', align: 'right' },
    { header: 'Type' },
    { header: 'Limit price', align: 'right' },
    { header: 'Status' },
    { header: 'Filled', align: 'right' },
    { header: 'Source' },
    { header: 'Actions', isMenu: true },
  ];

  let cancellingOrderIds = $state<number[]>([]);
  let cancelResult = $state<{ title: string; subtitle?: string; isError: boolean } | null>(null);

  async function cancelOrder(orderId: number): Promise<void> {
    cancelResult = null;
    cancellingOrderIds = [...cancellingOrderIds, orderId];
    const result = await cancelPaperOrder(fetch, orderId);
    cancellingOrderIds = cancellingOrderIds.filter((cancellingOrderId) => cancellingOrderId !== orderId);
    cancelResult =
      result.kind === 'failed'
        ? { title: `Order ${String(orderId)} not cancelled`, subtitle: result.message, isError: true }
        : { title: `Cancel request sent for order ${String(orderId)}`, isError: false };
  }

  function makeMenuItems(order: OpenOrder) {
    const cancelAction = describeCancelAction(order);
    return [
      {
        label: cancelAction.label,
        disabled: cancelAction.disabled || cancellingOrderIds.includes(order.order_id),
        onSelect: () => void cancelOrder(order.order_id),
      },
    ];
  }
</script>

<div class="open-orders">
  {#if cancelResult !== null}
    <InlineNotification
      kind={cancelResult.isError ? 'error' : 'success'}
      title={cancelResult.title}
      subtitle={cancelResult.subtitle}
      lowContrast
      onClose={() => (cancelResult = null)}
    />
  {/if}
  {#if orders.length === 0}
    <p>No open orders.</p>
  {:else}
    <ScrollRegion label="Open orders" maxHeight="18rem">
      <DataTable columns={COLUMNS} size="sm">
        {#snippet rows()}
          {#each orders as order (`${String(order.order_id)}-${order.source.kind}-${String(order.source.forward_test_id)}`)}
            <tr>
              <th scope="row">{order.symbol} <span class="exchange">{order.exchange}</span></th>
              <td>{order.side}</td>
              <td align="right">{order.quantity}</td>
              <td>{order.order_type} {order.time_in_force}</td>
              <td align="right">{formatAmount(order.limit_price)}</td>
              <td>{order.status}</td>
              <td align="right">{order.filled_quantity}</td>
              <td>{describeOrderSource(order.source)}</td>
              <td class="cds--table-column-menu">
                <OverflowMenu label={`Actions for order ${String(order.order_id)}`} items={makeMenuItems(order)} size="sm" />
              </td>
            </tr>
          {/each}
        {/snippet}
      </DataTable>
    </ScrollRegion>
  {/if}
</div>

<style>
  .open-orders {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  p {
    margin: 0;
  }

  .exchange {
    color: var(--cds-text-helper);
  }
</style>
