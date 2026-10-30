<!-- The positions of the paper account, one row for each owner of the owner ledger (section 11.7). A position that is not
     the sum of its owner positions has one more row with a warning icon and "Unattributed: <difference>". The symbol
     cell also shows the exchange, like the open orders. The unrealized
     P&L shows its sign, an arrow, and a color (ChangeText). With `fill`, the table takes the full height of a workbench
     panel and scrolls in it. With `compact` (the narrow panel of the instrument page), the table has no Currency and
     Market price columns, so all column names stay on one line. -->
<script lang="ts">
  import { DataTable, StatusIndicator, type TableColumn } from '#lib/foundation/carbon';
  import { EmptyText } from '#lib/foundation/empty_text';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { ChangeText, formatSignedNumber } from '#lib/foundation/value_format';
  import { formatAmount, listPositionRows, type PaperPosition } from './paper_account';

  interface Props {
    positions: PaperPosition[];
    fill?: boolean;
    compact?: boolean;
  }

  const { positions, fill = false, compact = false }: Props = $props();

  const COLUMNS: TableColumn[] = [
    { header: 'Symbol' },
    { header: 'Owner' },
    { header: 'Currency' },
    { header: 'Quantity', align: 'right' },
    { header: 'Average cost', align: 'right' },
    { header: 'Market price', align: 'right' },
    { header: 'Market value', align: 'right' },
    { header: 'Unrealized P&L', align: 'right' },
  ];
  const COMPACT_COLUMNS: TableColumn[] = [
    { header: 'Symbol' },
    { header: 'Owner' },
    { header: 'Quantity', align: 'right' },
    { header: 'Average cost', align: 'right' },
    { header: 'Market value', align: 'right' },
    { header: 'Unrealized P&L', align: 'right' },
  ];

  const positionRows = $derived(listPositionRows(positions));
</script>

{#if positions.length === 0}
  <EmptyText text="No positions" />
{:else}
  <ScrollRegion label="Positions" maxHeight="18rem" {fill}>
    <div class="positions">
      <DataTable columns={compact ? COMPACT_COLUMNS : COLUMNS} size="sm">
        {#snippet rows()}
          {#each positionRows as row (row.key)}
            {@const position = row.position}
            <tr>
              <th scope="row">{position.symbol} <span class="exchange">{position.exchange}</span></th>
              <td class="owner">
                {#if row.unattributed !== null}
                  <StatusIndicator kind="warning" label={row.unattributed} />
                {:else}
                  {row.owner ?? ''}
                {/if}
              </td>
              {#if !compact}
                <td>{position.currency}</td>
              {/if}
              <td align="right">{row.quantity ?? ''}</td>
              <td align="right">{row.averageCost === null ? '' : formatAmount(row.averageCost)}</td>
              {#if !compact}
                <td align="right">{row.unattributed === null ? formatAmount(position.market_price) : ''}</td>
              {/if}
              <td align="right">{row.marketValue === null ? '' : formatAmount(String(row.marketValue))}</td>
              <td align="right">
                {#if row.unrealizedPnl !== null}
                  <ChangeText value={row.unrealizedPnl} text={formatSignedNumber(row.unrealizedPnl)} />
                {/if}
              </td>
            </tr>
          {/each}
        {/snippet}
      </DataTable>
    </div>
  </ScrollRegion>
{/if}

<style>
  /* Column names stay on one line (32px header like all tables). */
  .positions :global(.cds--table-header-label),
  .positions th,
  .owner {
    white-space: nowrap;
  }

  .exchange {
    color: var(--cds-text-helper);
  }
</style>
