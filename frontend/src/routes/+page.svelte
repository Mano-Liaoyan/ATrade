<!-- Home page: the account overview workbench (foundation/workbench, #108). Left: the watchlist column with the
     instrument search, which adds to the watchlist; a watchlist instrument opens its instrument page. Main: the key
     numbers of the paper account in one line, over the Positions panel and the Orders panel (Open orders and Filled
     today), live from /ws/paper-trading. The open orders cancel from their row menu. The home page has no order form:
     paper orders are sent on the instrument page. -->
<script lang="ts">
  import { StatusIndicator } from '#lib/foundation/carbon';
  import { LiveUpdatesNotification } from '#lib/foundation/live_socket';
  import { Panel, PanelSplit, SideColumn, Workbench, type PanelSpec } from '#lib/foundation/workbench';
  import {
    describeBalanceCurrency,
    describePaperAccountCheck,
    FilledManualOrderList,
    findPaperAccountCheckKind,
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
  <SideColumn label="Watchlist" side="start" width="22rem" storageKey="atrade.home.watchlist-column">
    <InstrumentWatchlist editable />
  </SideColumn>

  <div class="overview">
    <LiveUpdatesNotification isConnected={accountFeed.isConnected} />
    <div class="key-numbers">
      {#if account === null || checkDescription === null}
        <StatusIndicator kind="in-progress" label="Reading the paper account." />
      {:else}
        {#if account.check.status !== 'passed'}
          <div class="check" role="status" aria-label="Paper account check">
            <StatusIndicator kind={findPaperAccountCheckKind(account.check.status)} label={checkDescription.title} />
            {#if checkDescription.detail !== null}
              <p class="check-detail">{checkDescription.detail}</p>
            {/if}
          </div>
        {/if}
        {#if account.balance !== null}
          <ul class="metrics" aria-label="Paper account balance">
            {#each listBalanceMetrics(account.balance) as metric (metric.label)}
              <li class="metric">
                <span class="metric-label">{metric.label}</span>
                <span class="metric-value">{metric.value}</span>
              </li>
            {/each}
          </ul>
          {#if account.balance.usd_per_base_unit === null}
            <StatusIndicator kind="error" label={describeBalanceCurrency(account.balance)} />
          {/if}
        {/if}
      {/if}
    </div>

    <PanelSplit storageKey="atrade.home.panel-split" panels={PANELS}>
      {#snippet panel(id, state)}
        {#if id === 'positions'}
          <Panel {...state} label="Positions">
            {#snippet header()}
              <h2>{withCount('Positions', account?.positions.length ?? 0)}</h2>
            {/snippet}
            <div class="table">
              {#if account === null}
                <p role="status">Reading the paper account.</p>
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

  /* The key numbers line: one surface level, a bottom divider like the panel header lines. */
  .key-numbers {
    display: flex;
    flex: none;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--cds-spacing-05) var(--cds-spacing-07);
    padding: var(--cds-spacing-05);
    box-shadow: inset 0 -1px 0 var(--cds-border-subtle-01);
  }

  .check-detail {
    margin: var(--cds-spacing-02) 0 0;
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
    color: var(--cds-text-secondary);
  }

  .metrics {
    display: flex;
    flex-wrap: wrap;
    gap: var(--cds-spacing-07);
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .metric {
    display: flex;
    flex-direction: column;
    gap: var(--cds-spacing-02);
  }

  .metric-label {
    font-size: var(--cds-label-01-font-size);
    line-height: var(--cds-label-01-line-height);
    letter-spacing: var(--cds-label-01-letter-spacing);
    color: var(--cds-text-secondary);
  }

  .metric-value {
    font-size: var(--cds-heading-03-font-size);
    font-weight: var(--cds-heading-03-font-weight);
    line-height: var(--cds-heading-03-line-height);
    font-variant-numeric: tabular-nums;
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
