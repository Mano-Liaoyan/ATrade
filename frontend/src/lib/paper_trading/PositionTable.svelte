<!-- The positions of the paper account, one row for each owner of the owner ledger (section 11.7). A position that is not
     the sum of its owner positions has one more row with the difference as its quantity and a warning icon before the
     symbol (tooltip "Unattributed: <difference>"). The symbol cell also shows the exchange, like the open orders. The unrealized
     P&L shows its sign, an arrow, and a color (ChangeText). With `fill`, the table takes the full height of a workbench
     panel and scrolls in it. With `compact` (the narrow panel of the instrument page), the table has no Currency and
     Market price columns, so all column names stay on one line. An instrument in the "Split check needed" state has one
     more row: a warning icon before the symbol (tooltip "Split check needed: 4:1"), the IBKR share count before and after, and (not in the compact
     table) the buttons "Apply split 4:1" and "Keep ledger" (section 11.11). -->
<script lang="ts">
  import {
    Button,
    DataTable,
    InlineNotification,
    StatusIndicator,
    type NotificationMessage,
    type TableColumn,
  } from '#lib/foundation/carbon';
  import { EmptyText } from '#lib/foundation/empty_text';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { ChangeText, formatSignedNumber } from '#lib/foundation/value_format';
  import { formatAmount, listPositionRows, type PaperPosition } from './paper_account';
  import { applyStockSplit, describeSplitCheck, keepLedger, type SplitCheck, type SplitCheckResult } from './stock_split';

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
  // The cells after the Quantity cell of a split check row: 4 in the full table, 3 in the compact table.
  const SPLIT_ACTION_COLSPAN = 4;
  const COMPACT_SPLIT_ACTION_COLSPAN = 3;
  const splitActionColspan = $derived(compact ? COMPACT_SPLIT_ACTION_COLSPAN : SPLIT_ACTION_COLSPAN);

  let resolvingSplitCheckIds = $state<number[]>([]);
  let splitCheckError = $state<NotificationMessage | null>(null);

  async function resolveSplitCheck(
    splitCheck: SplitCheck,
    action: (fetchFunction: typeof fetch, splitCheckId: number) => Promise<SplitCheckResult>,
  ): Promise<void> {
    splitCheckError = null;
    resolvingSplitCheckIds = [...resolvingSplitCheckIds, splitCheck.id];
    const result = await action(fetch, splitCheck.id);
    resolvingSplitCheckIds = resolvingSplitCheckIds.filter((id) => id !== splitCheck.id);
    if (result.kind === 'failed') {
      splitCheckError = { kind: 'error', title: 'Split check not changed', subtitle: result.message };
    }
  }
</script>

{#if splitCheckError !== null}
  <InlineNotification {...splitCheckError} onClose={() => (splitCheckError = null)} />
{/if}

{#if positions.length === 0}
  <EmptyText text="No positions" />
{:else}
  <ScrollRegion label="Positions" maxHeight="18rem" {fill}>
    <div class="positions">
      <DataTable columns={compact ? COMPACT_COLUMNS : COLUMNS} size="sm">
        {#snippet rows()}
          {#each positionRows as row (row.key)}
            {@const position = row.position}
            {#if row.splitCheck !== null}
              {@const splitCheck = row.splitCheck}
              {@const splitText = describeSplitCheck(splitCheck)}
              {@const isResolving = resolvingSplitCheckIds.includes(splitCheck.id)}
              <tr>
                <th scope="row">
                  <StatusIndicator kind="warning" label={`Split check needed: ${splitText.ratio}`} />{position.symbol}
                  <span class="exchange">{position.exchange}</span>
                </th>
                <td class="owner"></td>
                {#if !compact}
                  <td>{position.currency}</td>
                {/if}
                <td align="right">{splitText.shareCounts}</td>
                <td colspan={splitActionColspan}>
                  {#if !compact}
                    <div class="split-actions">
                      <Button
                        size="sm"
                        kind="primary"
                        disabled={isResolving}
                        onclick={() => void resolveSplitCheck(splitCheck, applyStockSplit)}>{splitText.applyLabel}</Button
                      >
                      <Button
                        size="sm"
                        kind="ghost"
                        disabled={isResolving}
                        onclick={() => void resolveSplitCheck(splitCheck, keepLedger)}>Keep ledger</Button
                      >
                    </div>
                  {/if}
                </td>
              </tr>
            {:else}
            <tr>
              <th scope="row">
                {#if row.unattributed !== null}
                  <StatusIndicator kind="warning" label={row.unattributed} />
                {/if}{position.symbol}
                <span class="exchange">{position.exchange}</span>
              </th>
              <td class="owner">{row.owner ?? ''}</td>
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
            {/if}
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

  .split-actions {
    display: flex;
    gap: var(--cds-spacing-03);
  }
</style>
