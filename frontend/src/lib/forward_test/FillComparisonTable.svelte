<!-- The fills of a forward test and of the backtest of the same period, one row for each bar and side
     (docs/architecture/forward_test.md section 12.10). A fill belongs to the last bar that ended before it.
     The difference is the forward test price minus the backtest price. The table scrolls inside its own region. -->
<script lang="ts">
  import { formatUtcTime } from '#lib/foundation/time_format';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import type { FillComparison } from './forward_test_api';

  const { fills }: { fills: FillComparison[] } = $props();

  const NO_FILL = '–';

  // Prices keep all their decimal places: a difference of less than one cent matters for a fill.
  function formatDifference(amount: string | null): string {
    if (amount === null) {
      return NO_FILL;
    }
    const sign = Number(amount) > 0 ? '+' : '';
    return `${sign}${amount}`;
  }
</script>

{#if fills.length === 0}
  <p>No fill on either side.</p>
{:else}
  <ScrollRegion label="Compared fills" maxHeight="min(20rem, 45vh)">
    <table class="fill-table">
      <thead>
        <tr>
          <th scope="col">Bar end</th>
          <th scope="col">Side</th>
          <th scope="col">Forward test quantity</th>
          <th scope="col">Forward test price (USD)</th>
          <th scope="col">Backtest quantity</th>
          <th scope="col">Backtest price (USD)</th>
          <th scope="col">Difference (USD)</th>
        </tr>
      </thead>
      <tbody>
        {#each fills as fill (`${fill.bar_end_utc} ${fill.side}`)}
          <tr>
            <th scope="row">{formatUtcTime(fill.bar_end_utc)}</th>
            <td>{fill.side}</td>
            <td class="number">{fill.forward_test_quantity_shares ?? NO_FILL}</td>
            <td class="number">{fill.forward_test_price_usd ?? NO_FILL}</td>
            <td class="number">{fill.backtest_quantity_shares ?? NO_FILL}</td>
            <td class="number">{fill.backtest_price_usd ?? NO_FILL}</td>
            <td class="number">{formatDifference(fill.price_difference_usd)}</td>
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

  /* A long value can break anywhere. A column name breaks only between words. */
  .fill-table td {
    overflow-wrap: anywhere;
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
