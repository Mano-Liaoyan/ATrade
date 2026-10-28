<!-- The fills of a forward test and of the backtest of the same period, one row for each bar and side
     (docs/architecture/forward_test.md section 12.10). A fill belongs to the last bar that ended before it.
     The difference is the forward test price minus the backtest price. The table fills its parent (a workbench panel) and scrolls inside its own region. -->
<script lang="ts">
  import { DataTable, type TableColumn } from '#lib/foundation/carbon';
  import { formatUtcTime } from '#lib/foundation/time_format';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import type { FillComparison } from './forward_test_api';

  const { fills }: { fills: FillComparison[] } = $props();

  const NO_FILL = '–';

  const COLUMNS: TableColumn[] = [
    { header: 'Bar end' },
    { header: 'Side' },
    { header: 'Forward test quantity', align: 'right' },
    { header: 'Forward test price (USD)', align: 'right' },
    { header: 'Backtest quantity', align: 'right' },
    { header: 'Backtest price (USD)', align: 'right' },
    { header: 'Difference (USD)', align: 'right' },
  ];

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
  <p class="empty-word">No fills</p>
{:else}
  <ScrollRegion label="Compared fills" fill>
    <div class="fill-comparison">
      <DataTable columns={COLUMNS} size="sm">
        {#snippet rows()}
          {#each fills as fill (`${fill.bar_end_utc} ${fill.side}`)}
            <tr>
              <th scope="row">{formatUtcTime(fill.bar_end_utc)}</th>
              <td>{fill.side}</td>
              <td align="right">{fill.forward_test_quantity_shares ?? NO_FILL}</td>
              <td align="right">{fill.forward_test_price_usd ?? NO_FILL}</td>
              <td align="right">{fill.backtest_quantity_shares ?? NO_FILL}</td>
              <td align="right">{fill.backtest_price_usd ?? NO_FILL}</td>
              <td align="right">{formatDifference(fill.price_difference_usd)}</td>
            </tr>
          {/each}
        {/snippet}
      </DataTable>
    </div>
  </ScrollRegion>
{/if}

<style>
  .empty-word {
    margin: 0;
    padding: var(--cds-spacing-05);
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
    color: var(--cds-text-secondary);
  }

  /* A long value can break anywhere. A column name breaks only between words. */
  .fill-comparison :global(td) {
    overflow-wrap: anywhere;
  }
</style>
