<!-- Home page: the account overview workbench (foundation/workbench, #108). Left: the watchlist column with the
     instrument search, which adds to the watchlist; a watchlist instrument opens its instrument page. Main: the key
     numbers of the paper account in one line, over the Positions panel and the Orders panel (Open orders and Filled
     today), live from /ws/paper-trading. The open orders cancel from their row menu. The home page has no order form:
     paper orders are sent on the instrument page. -->
<script lang="ts">
  import { InlineNotification } from '#lib/foundation/carbon';
  import { EmptyText } from '#lib/foundation/empty_text';
  import { LiveUpdatesNotification } from '#lib/foundation/live_socket';
  import { MetricRow, MetricTile } from '#lib/foundation/metric_tile';
  import { Panel, PanelSplit, SideColumn, Workbench, type PanelSpec } from '#lib/foundation/workbench';
  import {
    describeBalanceCurrency,
    describePaperAccountCheck,
    FilledManualOrderList,
    listBalanceMetrics,
    OpenOrderList,
    PaperAccountFeed,
    PositionTable,
  } from '#lib/paper_trading';
  import InstrumentWatchlist from './InstrumentWatchlist.svelte';

  const accountFeed = new PaperAccountFeed();
  $effect(() => accountFeed.start(fetch, window.location));
  const account = $derived(accountFeed.account);
  const checkDescription = $derived(account === null ? null : describePaperAccountCheck(account.check));

  const PANELS: PanelSpec[] = [
    { id: 'positions', minPixels: 96 },
    { id: 'orders', minPixels: 96, defaultPixels: 280, splitterLabel: 'Resize the positions and the orders' },
  ];

  function withCount(label: string, count: number): string {
    return count > 0 ? `${label} (${String(count)})` : label;
  }

  type OrdersTable = 'open-orders' | 'filled-today';
  let ordersTable: OrdersTable = $state('open-orders');
  const ordersTabItems = $derived([
    { value: 'open-orders', label: withCount('Open orders', accountFeed.openOrders.length) },
    { value: 'filled-today', label: withCount('Filled today', accountFeed.filledOrders.length) },
  ]);
</script>

<Workbench>
  <!-- 20rem like the watchlist of the instrument page, plus 2rem for the Delete column: the other columns have the same
       widths on both pages. -->
  <SideColumn label="Watchlist" side="start" width="22rem" storageKey="atrade.home.watchlist-column">
    <InstrumentWatchlist editable />
  </SideColumn>

  <div class="overview">
    <LiveUpdatesNotification isConnected={accountFeed.isConnected} />
    {#if account !== null && checkDescription !== null}
      {#if account.check.status !== 'passed'}
        <InlineNotification
          kind={account.check.status === 'failed' ? 'error' : 'warning'}
          label="Paper account check"
          title={checkDescription.title}
          subtitle={checkDescription.detail ?? undefined}
          lowContrast
        />
      {/if}
      {#if account.balance !== null}
        <MetricRow label="Paper account balance">
          {#each listBalanceMetrics(account.balance) as metric (metric.label)}
            <MetricTile name={metric.label} text={metric.value} />
          {/each}
        </MetricRow>
        {#if account.balance.usd_per_base_unit === null}
          <InlineNotification kind="error" title={describeBalanceCurrency(account.balance)} lowContrast />
        {/if}
      {/if}
    {/if}

    <PanelSplit storageKey="atrade.home.panel-split" panels={PANELS}>
      {#snippet panel(id, state)}
        {#if id === 'positions'}
          <Panel {...state} label="Positions">
            {#snippet header()}
              <h2>{withCount('Positions', account?.positions.length ?? 0)}</h2>
            {/snippet}
            <div class="table">
              {#if account === null}
                <EmptyText text="Loading" role="status" />
              {:else}
                <PositionTable positions={account.positions} fill />
              {/if}
            </div>
          </Panel>
        {:else}
          <Panel
            {...state}
            label="Orders"
            tabs={{
              label: 'Orders',
              items: ordersTabItems,
              value: ordersTable,
              onValueChange: (value: string) => {
                ordersTable = value as OrdersTable;
              },
            }}
          >
            <div class="table">
              {#if ordersTable === 'open-orders'}
                <OpenOrderList orders={accountFeed.openOrders} fill />
              {:else}
                <FilledManualOrderList orders={accountFeed.filledOrders} fill />
              {/if}
            </div>
          </Panel>
        {/if}
      {/snippet}
    </PanelSplit>
  </div>
</Workbench>

<style>
  .overview {
    display: flex;
    flex: 1 1 0;
    flex-direction: column;
    min-block-size: 0;
    min-inline-size: 0;
  }

  .table {
    display: flex;
    flex: 1;
    flex-direction: column;
    min-block-size: 0;
  }

  .table > :global(p),
  .table > :global(.open-orders > p) {
    margin: 0;
    padding: var(--cds-spacing-05);
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
    color: var(--cds-text-secondary);
  }
</style>
