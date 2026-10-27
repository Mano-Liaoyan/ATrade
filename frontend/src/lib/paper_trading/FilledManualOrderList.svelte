<!-- Filled orders by hand: the stored order and its fills from IBKR (docs/architecture/paper_trading.md section 11.4). -->
<script lang="ts">
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { formatAmount } from './paper_account';
  import type { ManualOrder } from './paper_orders';

  interface Props {
    orders: ManualOrder[];
  }

  const { orders }: Props = $props();
</script>

{#if orders.length === 0}
  <p>No filled orders by hand today.</p>
{:else}
  <ScrollRegion label="Filled orders by hand" maxHeight="18rem">
    <table class="orders">
      <thead>
        <tr>
          <th scope="col">Symbol</th>
          <th scope="col">Side</th>
          <th scope="col">Quantity</th>
          <th scope="col">Filled</th>
          <th scope="col">Average fill price</th>
          <th scope="col">Type</th>
          <th scope="col">Sent (UTC)</th>
        </tr>
      </thead>
      <tbody>
        {#each orders as order (order.id)}
          <tr>
            <th scope="row">{order.symbol} <span class="exchange">{order.exchange}</span></th>
            <td>{order.side}</td>
            <td class="number">{order.quantity}</td>
            <td class="number">{order.filled_quantity}</td>
            <td class="number">{formatAmount(order.average_fill_price)}</td>
            <td>{order.order_type} {order.time_in_force}</td>
            <td>{order.created_at_utc}</td>
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
</style>
