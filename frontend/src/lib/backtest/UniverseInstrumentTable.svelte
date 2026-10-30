<!-- The Instruments tab of a multi-instrument backtest: one row for each universe member with its trade count, net
     profit, and quarters in the universe as right-aligned tabular numbers (docs/architecture/backtest.md 10.10.7). It
     fills the height of its panel body and scrolls in itself. -->
<script lang="ts">
  import { DataTable, type TableColumn } from '#lib/foundation/carbon';
  import { EmptyText } from '#lib/foundation/empty_text';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import type { UniverseInstrument } from './backtest_api';
  import { formatUsd } from './backtest_format';

  const { instruments }: { instruments: UniverseInstrument[] } = $props();

  const COLUMNS: TableColumn[] = [
    { header: 'Instrument' },
    { header: 'Trades', align: 'right' },
    { header: 'Net profit (USD)', align: 'right' },
    { header: 'Quarters', align: 'right' },
  ];
</script>

{#if instruments.length === 0}
  <EmptyText text="No instruments" />
{:else}
  <ScrollRegion label="Instruments" fill>
    <DataTable columns={COLUMNS} size="sm">
      {#snippet rows()}
        {#each instruments as instrument (`${instrument.symbol}:${instrument.exchange}`)}
          <tr>
            <td>{instrument.symbol}</td>
            <td align="right">{instrument.trade_count}</td>
            <td align="right">{formatUsd(instrument.net_profit_usd)}</td>
            <td align="right">{instrument.quarter_count}</td>
          </tr>
        {/each}
      {/snippet}
    </DataTable>
  </ScrollRegion>
{/if}
