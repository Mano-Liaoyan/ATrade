<!-- The positions of the paper account. The symbol cell also shows the exchange, like the open orders. The unrealized
     P&L shows its sign, an arrow, and a color (ChangeText). With `fill`, the table takes the full height of a workbench
     panel and scrolls in it. With `compact` (the narrow panel of the instrument page), the table has no Currency and
     Market price columns, so all column names stay on one line. -->
<script lang="ts">
  import { DataTable, type TableColumn } from '#lib/foundation/carbon';
  import { EmptyText } from '#lib/foundation/empty_text';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { ChangeText, formatSignedNumber } from '#lib/foundation/value_format';
  import { formatAmount, type PaperPosition } from './paper_account';

  interface Props {
    positions: PaperPosition[];
    fill?: boolean;
    compact?: boolean;
  }

  const { positions, fill = false, compact = false }: Props = $props();

  const COLUMNS: TableColumn[] = [
    { header: 'Symbol' },
    { header: 'Currency' },
    { header: 'Quantity', align: 'right' },
    { header: 'Average cost', align: 'right' },
    { header: 'Market price', align: 'right' },
    { header: 'Market value', align: 'right' },
    { header: 'Unrealized P&L', align: 'right' },
  ];
  const COMPACT_COLUMNS: TableColumn[] = [
    { header: 'Symbol' },
    { header: 'Quantity', align: 'right' },
    { header: 'Average cost', align: 'right' },
    { header: 'Market value', align: 'right' },
    { header: 'Unrealized P&L', align: 'right' },
  ];
</script>

{#if positions.length === 0}
  <EmptyText text="No positions" />
{:else}
  <ScrollRegion label="Positions" maxHeight="18rem" {fill}>
    <div class="positions">
      <DataTable columns={compact ? COMPACT_COLUMNS : COLUMNS} size="sm">
        {#snippet rows()}
          {#each positions as position (`${position.symbol}-${position.exchange}-${position.security_type}`)}
            {@const unrealizedPnl = Number(position.unrealized_pnl)}
            <tr>
              <th scope="row">{position.symbol} <span class="exchange">{position.exchange}</span></th>
              {#if !compact}
                <td>{position.currency}</td>
              {/if}
              <td align="right">{position.quantity}</td>
              <td align="right">{formatAmount(position.average_cost)}</td>
              {#if !compact}
                <td align="right">{formatAmount(position.market_price)}</td>
              {/if}
              <td align="right">{formatAmount(position.market_value)}</td>
              <td align="right"><ChangeText value={unrealizedPnl} text={formatSignedNumber(unrealizedPnl)} /></td>
            </tr>
          {/each}
        {/snippet}
      </DataTable>
    </div>
  </ScrollRegion>
{/if}

<style>
  /* Column names stay on one line (32px header like all tables). */
  .positions :global(.cds--table-header-label) {
    white-space: nowrap;
  }

  .exchange {
    color: var(--cds-text-helper);
  }
</style>
