<!-- The recorded fills of one forward test (docs/architecture/forward_test.md section 12.8), oldest first. -->
<script lang="ts">
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { formatUtcTime } from '#lib/foundation/time_format';
  import { formatAmount } from '#lib/foundation/value_format';
  import type { ForwardTestFill } from './forward_test_api';

  const { fills }: { fills: ForwardTestFill[] } = $props();
</script>

{#if fills.length === 0}
  <p>No fill yet.</p>
{:else}
  <ScrollRegion label="Forward test fills" maxHeight="min(20rem, 45vh)">
    <table class="fill-table">
      <thead>
        <tr>
          <th scope="col">Time</th>
          <th scope="col">Side</th>
          <th scope="col">Quantity</th>
          <th scope="col">Price (USD)</th>
          <th scope="col">Commission (USD)</th>
        </tr>
      </thead>
      <tbody>
        {#each fills as fill, fillIndex (fillIndex)}
          <tr>
            <th scope="row">{formatUtcTime(fill.time_utc)}</th>
            <td>{fill.side}</td>
            <td class="number">{fill.quantity_shares}</td>
            <td class="number">{formatAmount(fill.price_usd)}</td>
            <td class="number">{formatAmount(fill.commission_usd)}</td>
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

  .fill-table {
    border-collapse: collapse;
    inline-size: 100%;
    font-size: 0.875rem;
  }

  .fill-table th,
  .fill-table td {
    padding: 0.375rem 0.75rem;
    border-bottom: 1px solid var(--color-border);
    text-align: start;
  }

  .fill-table thead th {
    position: sticky;
    inset-block-start: 0;
    background: var(--color-surface);
  }

  .fill-table .number {
    text-align: end;
    font-variant-numeric: tabular-nums;
  }
</style>
