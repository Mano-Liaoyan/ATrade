<!-- PROTOTYPE (#99), throwaway: the tabs under the chart: positions, open orders, and filled orders by hand of today,
     from /ws/paper-trading and /api/paper-trading/manual-orders. Each tab panel has its own scroll region. -->
<script lang="ts">
  import { DataTable, InlineNotification, OverflowMenu, Tabs, type NotificationMessage, type TableColumn } from '#lib/foundation/carbon';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { formatUtcTime } from '#lib/foundation/time_format';
  import { cancelPaperOrder, formatAmount, type ManualOrder, type OpenOrder, type PaperPosition } from '#lib/paper_trading';
  import type { Snippet } from 'svelte';
  import { findAmountDirection, formatSignedAmount } from './instrument_quote';
  import { isEmptyHeaderTarget } from './workbench_panels';

  interface Props {
    positions: PaperPosition[] | null;
    openOrders: OpenOrder[];
    filledOrders: ManualOrder[];
    // PROTOTYPE (#99): the panel shows only its tab line. A tab click calls onTabSelect, so the parent can restore it.
    headerOnly?: boolean;
    onTabSelect?: () => void;
    onHeaderDoubleClick?: () => void;
    // The panel buttons at the right end of the tab line.
    actions?: Snippet;
  }

  const {
    positions,
    openOrders,
    filledOrders,
    headerOnly = false,
    onTabSelect,
    onHeaderDoubleClick,
    actions,
  }: Props = $props();

  // Double-click on the empty part of the tab line. An attachment, because the tab line belongs to the Tabs component.
  function toggleOnHeaderDoubleClick(panel: HTMLElement) {
    const toggle = (event: MouseEvent): void => {
      const tabLine = panel.querySelector<HTMLElement>('.cds--tabs');
      if (tabLine !== null && isEmptyHeaderTarget(event.target, tabLine)) {
        onHeaderDoubleClick?.();
      }
    };
    panel.addEventListener('dblclick', toggle);
    return () => {
      panel.removeEventListener('dblclick', toggle);
    };
  }

  type AccountTab = 'positions' | 'open-orders' | 'filled-today';

  const TABS: readonly { value: AccountTab; label: string }[] = [
    { value: 'positions', label: 'Positions' },
    { value: 'open-orders', label: 'Open orders' },
    { value: 'filled-today', label: 'Filled today' },
  ];

  const POSITION_COLUMNS: TableColumn[] = [
    { header: 'Symbol' },
    { header: 'Quantity', align: 'right' },
    { header: 'Average cost', align: 'right' },
    { header: 'Market price', align: 'right' },
    { header: 'Market value', align: 'right' },
    { header: 'Unrealized P&L', align: 'right' },
  ];

  const OPEN_ORDER_COLUMNS: TableColumn[] = [
    { header: 'Symbol' },
    { header: 'Side' },
    { header: 'Quantity', align: 'right' },
    { header: 'Type' },
    { header: 'Limit price', align: 'right' },
    { header: 'Status' },
    { header: 'Filled', align: 'right' },
    { header: 'Actions', isMenu: true },
  ];

  const FILLED_COLUMNS: TableColumn[] = [
    { header: 'Symbol' },
    { header: 'Side' },
    { header: 'Filled', align: 'right' },
    { header: 'Average fill price', align: 'right' },
    { header: 'Type' },
    { header: 'Sent' },
  ];

  let selectedTab = $state<AccountTab>('positions');
  let cancelResult = $state<NotificationMessage | null>(null);

  const tabItems = $derived(
    TABS.map((tab) => {
      const count = { positions: positions?.length ?? 0, 'open-orders': openOrders.length, 'filled-today': filledOrders.length }[tab.value];
      return { value: tab.value, label: count > 0 ? `${tab.label} (${String(count)})` : tab.label };
    }),
  );

  async function cancelOrder(orderId: number): Promise<void> {
    cancelResult = null;
    const result = await cancelPaperOrder(fetch, orderId);
    cancelResult =
      result.kind === 'failed'
        ? { kind: 'error', title: `Order ${String(orderId)} not cancelled`, subtitle: result.message }
        : { kind: 'success', title: `Cancel request sent for order ${String(orderId)}` };
  }
</script>

<div class={['account-tabs', headerOnly && 'account-tabs--header-only']} {@attach toggleOnHeaderDoubleClick}>
  {#if actions !== undefined}
    <div class="panel-actions">{@render actions()}</div>
  {/if}
  <Tabs
    label="Paper account"
    items={tabItems}
    value={selectedTab}
    onValueChange={(value: string) => {
      selectedTab = value as AccountTab;
      onTabSelect?.();
    }}
  >
    {#snippet panel()}
      {#if cancelResult !== null}
        <InlineNotification {...cancelResult} lowContrast onClose={() => (cancelResult = null)} />
      {/if}
      {#if selectedTab === 'positions'}
        {#if positions === null || positions.length === 0}
          <p class="empty">{positions === null ? 'Reading the paper account.' : 'No positions'}</p>
        {:else}
          {@const accountPositions = positions}
          <ScrollRegion label="Positions" maxHeight="100%">
            <DataTable columns={POSITION_COLUMNS} size="sm">
              {#snippet rows()}
                {#each accountPositions as position (`${position.symbol}-${position.exchange}-${position.security_type}`)}
                  {@const direction = findAmountDirection(position.unrealized_pnl)}
                  <tr>
                    <th scope="row">{position.symbol} <span class="secondary">{position.exchange}</span></th>
                    <td align="right">{position.quantity}</td>
                    <td align="right">{formatAmount(position.average_cost)}</td>
                    <td align="right">{formatAmount(position.market_price)}</td>
                    <td align="right">{formatAmount(position.market_value)}</td>
                    <td align="right" class={`signed signed--${direction}`}>{formatSignedAmount(position.unrealized_pnl)}</td>
                  </tr>
                {/each}
              {/snippet}
            </DataTable>
          </ScrollRegion>
        {/if}
      {:else if selectedTab === 'open-orders'}
        {#if openOrders.length === 0}
          <p class="empty">No open orders</p>
        {:else}
          <ScrollRegion label="Open orders" maxHeight="100%">
            <DataTable columns={OPEN_ORDER_COLUMNS} size="sm">
              {#snippet rows()}
                {#each openOrders as order (`${String(order.order_id)}-${order.source.kind}-${String(order.source.forward_test_id)}`)}
                  <tr>
                    <th scope="row">{order.symbol} <span class="secondary">{order.exchange}</span></th>
                    <td>{order.side}</td>
                    <td align="right">{order.quantity}</td>
                    <td>{order.order_type} {order.time_in_force}</td>
                    <td align="right">{formatAmount(order.limit_price)}</td>
                    <td>{order.status}</td>
                    <td align="right">{order.filled_quantity}</td>
                    <td class="cds--table-column-menu">
                      <OverflowMenu
                        label={`Actions for order ${String(order.order_id)}`}
                        size="sm"
                        items={[
                          {
                            label: order.can_cancel ? 'Cancel order' : 'Cancel order (not an order by hand)',
                            disabled: !order.can_cancel,
                            danger: true,
                            onSelect: () => void cancelOrder(order.order_id),
                          },
                        ]}
                      />
                    </td>
                  </tr>
                {/each}
              {/snippet}
            </DataTable>
          </ScrollRegion>
        {/if}
      {:else if filledOrders.length === 0}
        <p class="empty">No filled orders today</p>
      {:else}
        <ScrollRegion label="Filled today" maxHeight="100%">
          <DataTable columns={FILLED_COLUMNS} size="sm">
            {#snippet rows()}
              {#each filledOrders as order (order.id)}
                <tr>
                  <th scope="row">{order.symbol} <span class="secondary">{order.exchange}</span></th>
                  <td>{order.side}</td>
                  <td align="right">{order.filled_quantity}</td>
                  <td align="right">{formatAmount(order.average_fill_price)}</td>
                  <td>{order.order_type} {order.time_in_force}</td>
                  <td>{formatUtcTime(order.created_at_utc)}</td>
                </tr>
              {/each}
            {/snippet}
          </DataTable>
        </ScrollRegion>
      {/if}
    {/snippet}
  </Tabs>
</div>

<style>
  /* The tab list is one line. The panel fills the rest of the height, and its table scrolls in it. */
  .account-tabs {
    position: relative;
    block-size: 100%;
    min-block-size: 0;
  }

  /* The panel buttons sit on the tab line, at its right end. The tab line has the Carbon tab height (2.5rem). */
  .panel-actions {
    position: absolute;
    z-index: 1;
    inset-block-start: 0;
    inset-inline-end: 0;
    display: flex;
    align-items: center;
    block-size: var(--cds-spacing-08);
    padding-inline-end: var(--cds-spacing-02);
  }

  .account-tabs :global(.cds--tabs) {
    padding-inline-end: calc(var(--cds-spacing-08) * 2);
  }

  .account-tabs--header-only :global(.cds--tab-content) {
    display: none;
  }

  .account-tabs > :global([data-tabs-root]) {
    display: grid;
    grid-template-rows: auto minmax(0, 1fr);
    block-size: 100%;
  }

  .account-tabs :global(.cds--tab-content) {
    display: flex;
    flex-direction: column;
    min-block-size: 0;
    padding: 0;
  }

  .account-tabs :global(.cds--tab-content > .scroll-region) {
    flex: 1;
    min-block-size: 0;
  }

  .secondary {
    color: var(--cds-text-secondary);
  }

  .signed--up {
    color: var(--cds-support-success);
  }

  .signed--down {
    color: var(--cds-support-error);
  }

  .empty {
    margin: 0;
    padding: var(--cds-spacing-05);
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
    letter-spacing: var(--cds-body-compact-01-letter-spacing);
    color: var(--cds-text-secondary);
  }
</style>
