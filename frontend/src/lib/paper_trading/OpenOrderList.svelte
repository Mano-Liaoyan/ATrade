<!-- Open orders of the paper account from IBKR, with the source of each order. Only orders by hand can be cancelled. -->
<script lang="ts">
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { formatAmount } from './paper_account';
  import { cancelPaperOrder, describeOrderSource, type OpenOrder } from './paper_orders';

  interface Props {
    orders: OpenOrder[];
  }

  const { orders }: Props = $props();

  let cancellingOrderIds = $state<number[]>([]);
  let cancelMessage = $state<string | null>(null);

  async function cancelOrder(orderId: number): Promise<void> {
    cancelMessage = null;
    cancellingOrderIds = [...cancellingOrderIds, orderId];
    const result = await cancelPaperOrder(fetch, orderId);
    cancellingOrderIds = cancellingOrderIds.filter((cancellingOrderId) => cancellingOrderId !== orderId);
    if (result.kind === 'failed') {
      cancelMessage = result.message;
    }
  }
</script>

{#if cancelMessage !== null}
  <p class="cancel-message" role="alert">{cancelMessage}</p>
{/if}
{#if orders.length === 0}
  <p>No open orders.</p>
{:else}
  <ScrollRegion label="Open orders" maxHeight="18rem">
    <table class="orders">
      <thead>
        <tr>
          <th scope="col">Symbol</th>
          <th scope="col">Side</th>
          <th scope="col">Quantity</th>
          <th scope="col">Type</th>
          <th scope="col">Limit price</th>
          <th scope="col">Status</th>
          <th scope="col">Filled</th>
          <th scope="col">Source</th>
          <th scope="col"><span class="visually-hidden">Action</span></th>
        </tr>
      </thead>
      <tbody>
        {#each orders as order (`${String(order.order_id)}-${order.source.kind}-${String(order.source.forward_test_id)}`)}
          <tr>
            <th scope="row">{order.symbol} <span class="exchange">{order.exchange}</span></th>
            <td>{order.side}</td>
            <td class="number">{order.quantity}</td>
            <td>{order.order_type} {order.time_in_force}</td>
            <td class="number">{formatAmount(order.limit_price)}</td>
            <td>{order.status}</td>
            <td class="number">{order.filled_quantity}</td>
            <td>{describeOrderSource(order.source)}</td>
            <td>
              {#if order.can_cancel}
                <button
                  type="button"
                  aria-label={`Cancel order ${String(order.order_id)}`}
                  disabled={cancellingOrderIds.includes(order.order_id)}
                  onclick={() => cancelOrder(order.order_id)}>Cancel</button
                >
              {/if}
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </ScrollRegion>
{/if}

<style>
  p {
    margin: 0;
  }

  .cancel-message {
    color: var(--color-warning);
    font-weight: 600;
  }

  .orders {
    border-collapse: collapse;
    inline-size: 100%;
    font-size: 0.875rem;
  }

  .orders th,
  .orders td {
    padding: 0.375rem 0.75rem;
    border-bottom: 1px solid var(--color-border);
    text-align: start;
  }

  .orders thead th {
    position: sticky;
    inset-block-start: 0;
    background: var(--color-surface);
  }

  .orders .number {
    text-align: end;
    font-variant-numeric: tabular-nums;
  }

  .exchange {
    color: var(--color-muted);
    font-weight: normal;
  }

  .visually-hidden {
    position: absolute;
    inline-size: 1px;
    block-size: 1px;
    overflow: hidden;
    clip-path: inset(50%);
    white-space: nowrap;
  }
</style>
