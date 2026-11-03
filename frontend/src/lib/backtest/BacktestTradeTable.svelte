<!-- The trades of a backtest in 32px rows: number, time, symbol, side, quantity, price, and commission, with right-aligned
     tabular numbers. It fills the height of its panel body and scrolls in itself. The backtest page and the strategy
     page show it in their Trades tab. With `onRowSelect` (the backtest page with the bar chart, docs/architecture/
     indicator.md section 23.9.9), the pointer or the focus on a row gives `onRowPoint` its index, and a click on a row
     or Enter selects the row. The selected row has the Carbon selected row color. -->
<script lang="ts">
  import { DataTable, SelectableTableRow, type TableColumn } from '#lib/foundation/carbon';
  import { EmptyText } from '#lib/foundation/empty_text';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { formatUtcTime } from '#lib/foundation/time_format';
  import { MISSING_VALUE } from '#lib/foundation/value_format';
  import type { BacktestTrade } from './backtest_api';
  import { formatUsd } from './backtest_format';

  interface Props {
    trades: BacktestTrade[];
    selectedIndex?: number | null;
    onRowPoint?: (index: number | null) => void;
    onRowSelect?: (index: number) => void;
  }

  const { trades, selectedIndex = null, onRowPoint, onRowSelect }: Props = $props();

  const TRADE_COLUMNS: TableColumn[] = [
    { header: '#', align: 'right' },
    { header: 'Time' },
    { header: 'Symbol' },
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
          {#if onRowSelect === undefined}
            <tr>
              <th scope="row" align="right">{tradeIndex + 1}</th>
              {@render cells(trade)}
            </tr>
          {:else}
            <SelectableTableRow
              index={tradeIndex}
              isSelected={tradeIndex === selectedIndex}
              {onRowPoint}
              {onRowSelect}
            >
              {@render cells(trade)}
            </SelectableTableRow>
          {/if}
        {/each}
      {/snippet}
    </DataTable>
  </ScrollRegion>
{/if}

{#snippet cells(trade: BacktestTrade)}
  <td>{formatUtcTime(trade.time_utc)}</td>
  <td>{trade.symbol ?? MISSING_VALUE}</td>
  <td>{trade.side}</td>
  <td align="right">{trade.quantity_shares}</td>
  <td align="right">{formatUsd(trade.price_usd)}</td>
  <td align="right">{formatUsd(trade.commission_usd)}</td>
{/snippet}
