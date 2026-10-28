<!-- The trades of a backtest in 32px rows: number, time, side, quantity, price, and commission, with right-aligned
     tabular numbers. It fills the height of its panel body and scrolls in itself. The backtest page and the strategy
     page show it in their Trades tab. -->
<script lang="ts">
  import { DataTable, type TableColumn } from '#lib/foundation/carbon';
  import { EmptyText } from '#lib/foundation/empty_text';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { formatUtcTime } from '#lib/foundation/time_format';
  import type { BacktestTrade } from './backtest_api';
  import { formatUsd } from './backtest_format';

  const { trades }: { trades: BacktestTrade[] } = $props();

  const TRADE_COLUMNS: TableColumn[] = [
    { header: '#', align: 'right' },
    { header: 'Time' },
    { header: 'Side' },
    { header: 'Quantity', align: 'right' },
    { header: 'Price (USD)', align: 'right' },
    { header: 'Commission (USD)', align: 'right' },
  ];
</script>

{#if trades.length === 0}
  <EmptyText text="No trades" />
{:else}
  <ScrollRegion label="Trades" fill>
    <DataTable columns={TRADE_COLUMNS} size="sm">
      {#snippet rows()}
        {#each trades as trade, tradeIndex (tradeIndex)}
          <tr>
            <th scope="row" align="right">{tradeIndex + 1}</th>
            <td>{formatUtcTime(trade.time_utc)}</td>
            <td>{trade.side}</td>
            <td align="right">{trade.quantity_shares}</td>
            <td align="right">{formatUsd(trade.price_usd)}</td>
            <td align="right">{formatUsd(trade.commission_usd)}</td>
          </tr>
        {/each}
      {/snippet}
    </DataTable>
  </ScrollRegion>
{/if}
