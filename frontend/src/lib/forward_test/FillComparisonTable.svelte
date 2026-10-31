<!-- The fills of a forward test and of the backtest of the same period, one row for each bar, side, and instrument
     (docs/architecture/forward_test.md section 12.10). The Symbol column is only for a multi-instrument forward test. A fill belongs to the last bar that ended before it.
     The difference is the forward test price minus the backtest price. The table fills its parent (a workbench panel) and scrolls inside its own region. -->
<script lang="ts">
  import { DataTable, type TableColumn } from '#lib/foundation/carbon';
  import { EmptyText } from '#lib/foundation/empty_text';
  import { formatUtcTime } from '#lib/foundation/time_format';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import type { FillComparison } from './forward_test_api';

  const { fills, showsSymbol }: { fills: FillComparison[]; showsSymbol: boolean } = $props();

  const NO_FILL = '–';

  const columns: TableColumn[] = $derived([
    { header: 'Bar end' },
    ...(showsSymbol ? [{ header: 'Symbol' }] : []),
    { header: 'Side' },
    { header: 'Forward test quantity', align: 'right' },
    { header: 'Forward test price (USD)', align: 'right' },
    { header: 'Backtest quantity', align: 'right' },
    { header: 'Backtest price (USD)', align: 'right' },
    { header: 'Difference (USD)', align: 'right' },
  ]);

  // Prices keep all their decimal places: a difference of less than one cent matters for a fill. So this column does
  // not use formatSignedNumber (2 decimal places); it adds the same "+" to a positive difference. A price difference is
  // not a gain or a loss, so it has no up or down icon.
  function formatDifference(amount: string | null): string {
    if (amount === null) {
      return NO_FILL;
    }
    const sign = Number(amount) > 0 ? '+' : '';
    return `${sign}${amount}`;
  }
</script>

{#if fills.length === 0}
  <EmptyText text="No fills" />
{:else}
  <ScrollRegion label="Compared fills" fill>
    <div class="fill-comparison">
      <DataTable {columns} size="sm">
        {#snippet rows()}
          {#each fills as fill (`${fill.bar_end_utc} ${fill.side} ${fill.symbol} ${fill.exchange}`)}
            <tr>
              <th scope="row">{formatUtcTime(fill.bar_end_utc)}</th>
              {#if showsSymbol}
                <td>{fill.symbol}</td>
              {/if}
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
  /* A long value can break anywhere. A column name breaks only between words. The bar end stays on one line, like
     the times of the other tables. */
  .fill-comparison :global(td) {
    overflow-wrap: anywhere;
  }

  .fill-comparison :global(tbody th) {
    white-space: nowrap;
  }
</style>
