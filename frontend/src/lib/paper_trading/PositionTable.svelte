<!-- The positions of the paper account. The unrealized P&L shows its sign, an arrow, and a color (ChangeText).
     With `fill`, the table takes the full height of a workbench panel and scrolls in it. -->
<script lang="ts">
  import { DataTable, type TableColumn } from '#lib/foundation/carbon';
  import { EmptyText } from '#lib/foundation/empty_text';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { ChangeText, formatSignedNumber } from '#lib/foundation/value_format';
  import { formatAmount, type PaperPosition } from './paper_account';

  interface Props {
    positions: PaperPosition[];
    fill?: boolean;
  }

  const { positions, fill = false }: Props = $props();

  const COLUMNS: TableColumn[] = [
    { header: 'Symbol' },
    { header: 'Exchange' },
    { header: 'Currency' },
    { header: 'Quantity', align: 'right' },
    { header: 'Average cost', align: 'right' },
    { header: 'Market price', align: 'right' },
    { header: 'Market value', align: 'right' },
    { header: 'Unrealized P&L', align: 'right' },
  ];
</script>

{#if positions.length === 0}
  <EmptyText text="No positions" />
{:else}
  <ScrollRegion label="Positions" maxHeight="18rem" {fill}>
    <DataTable columns={COLUMNS} size="sm">
      {#snippet rows()}
        {#each positions as position (`${position.symbol}-${position.exchange}-${position.security_type}`)}
          {@const unrealizedPnl = Number(position.unrealized_pnl)}
          <tr>
            <th scope="row">{position.symbol}</th>
            <td>{position.exchange}</td>
            <td>{position.currency}</td>
            <td align="right">{position.quantity}</td>
            <td align="right">{formatAmount(position.average_cost)}</td>
            <td align="right">{formatAmount(position.market_price)}</td>
            <td align="right">{formatAmount(position.market_value)}</td>
            <td align="right"><ChangeText value={unrealizedPnl} text={formatSignedNumber(unrealizedPnl)} /></td>
          </tr>
        {/each}
      {/snippet}
    </DataTable>
  </ScrollRegion>
{/if}

