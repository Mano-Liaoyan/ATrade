<!-- Account panel: the paper account check, the balance, the positions, the order form, and the open orders,
     updated live from /ws/paper-trading. -->
<script lang="ts">
  import { buildSocketUrl, openLiveSocket } from '#lib/foundation/live_socket';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import {
    describeBalanceCurrency,
    describePaperAccountCheck,
    formatAmount,
    PAPER_TRADING_SOCKET_PATH,
    readPaperAccountMessage,
    type PaperAccountMessage,
  } from './paper_account';
  import FilledManualOrderList from './FilledManualOrderList.svelte';
  import OpenOrderList from './OpenOrderList.svelte';
  import { readFilledManualOrders, readOpenOrdersMessage, type ManualOrder, type OpenOrder } from './paper_orders';
  import PaperOrderTicket from './PaperOrderTicket.svelte';

  let account = $state<PaperAccountMessage | null>(null);
  let isSocketConnected = $state(false);
  let openOrders = $state<OpenOrder[]>([]);
  let filledManualOrders = $state<ManualOrder[]>([]);

  // A fill changes the open orders, and the server sends the orders message only after a change.
  async function refreshFilledManualOrders(): Promise<void> {
    const orders = await readFilledManualOrders(fetch);
    if (orders !== null) {
      filledManualOrders = orders;
    }
  }

  const checkDescription = $derived(account === null ? null : describePaperAccountCheck(account.check));

  $effect(() => {
    return openLiveSocket({
      url: buildSocketUrl(PAPER_TRADING_SOCKET_PATH, window.location),
      onMessage: (message) => {
        const accountMessage = readPaperAccountMessage(message);
        if (accountMessage !== null) {
          account = accountMessage;
        }
        const ordersMessage = readOpenOrdersMessage(message);
        if (ordersMessage !== null) {
          openOrders = ordersMessage;
          void refreshFilledManualOrders();
        }
      },
      onConnectionChange: (isConnected) => {
        isSocketConnected = isConnected;
      },
    });
  });
</script>

<section class="account-panel" aria-labelledby="account-panel-title">
  <header class="panel-header">
    <h2 id="account-panel-title">Paper account <span class="paper-mark">PAPER</span></h2>
    {#if !isSocketConnected}
      <span class="live-status">Live updates paused. ATrade connects again.</span>
    {/if}
  </header>

  {#if account === null || checkDescription === null}
    <p role="status" aria-label="Paper account check">Reading the paper account.</p>
  {:else}
    <div
      class="account-check"
      class:check-failed={account.check.status === 'failed'}
      role="status"
      aria-label="Paper account check"
    >
      <p class="check-title">{checkDescription.title}</p>
      {#if checkDescription.detail !== null}
        <p class="check-detail">{checkDescription.detail}</p>
      {/if}
    </div>

    {#if account.balance !== null}
      <dl class="balance" aria-label="Balance">
        <div>
          <dt>Net liquidation (USD)</dt>
          <dd>{formatAmount(account.balance.net_liquidation_usd)}</dd>
        </div>
        <div>
          <dt>Cash (USD)</dt>
          <dd>{formatAmount(account.balance.cash_usd)}</dd>
        </div>
        {#if account.balance.base_currency !== null && account.balance.base_currency !== 'USD'}
          <div>
            <dt>Net liquidation ({account.balance.base_currency})</dt>
            <dd>{formatAmount(account.balance.net_liquidation_base)}</dd>
          </div>
        {/if}
      </dl>
      <p
        class="balance-currency"
        class:balance-failed={account.balance.usd_per_base_unit === null}
        role="note"
        aria-label="Balance currency"
      >
        {describeBalanceCurrency(account.balance)}
      </p>

      <h3>Positions</h3>
      {#if account.positions.length === 0}
        <p>No positions.</p>
      {:else}
        <ScrollRegion label="Positions" maxHeight="18rem">
          <table class="positions">
            <thead>
              <tr>
                <th scope="col">Symbol</th>
                <th scope="col">Exchange</th>
                <th scope="col">Currency</th>
                <th scope="col">Quantity</th>
                <th scope="col">Average cost</th>
                <th scope="col">Market price</th>
                <th scope="col">Market value</th>
                <th scope="col">Unrealized P&amp;L</th>
              </tr>
            </thead>
            <tbody>
              {#each account.positions as position (`${position.symbol}-${position.exchange}-${position.security_type}`)}
                <tr>
                  <th scope="row">{position.symbol}</th>
                  <td>{position.exchange}</td>
                  <td>{position.currency}</td>
                  <td class="number">{position.quantity}</td>
                  <td class="number">{formatAmount(position.average_cost)}</td>
                  <td class="number">{formatAmount(position.market_price)}</td>
                  <td class="number">{formatAmount(position.market_value)}</td>
                  <td class="number">{formatAmount(position.unrealized_pnl)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </ScrollRegion>
      {/if}
    {/if}

    {#if account.check.status === 'passed' && account.check.actual_accounts[0] !== undefined}
      <h3>New paper order</h3>
      <PaperOrderTicket accountId={account.check.actual_accounts[0]} />
    {/if}

    <h3>Open orders</h3>
    <OpenOrderList orders={openOrders} />

    <h3>Filled orders by hand</h3>
    <FilledManualOrderList orders={filledManualOrders} />
  {/if}
</section>

<style>
  .account-panel {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    max-inline-size: 60rem;
    padding: 1rem;
    border: 1px solid var(--color-border);
    border-radius: 0.5rem;
    background: var(--color-surface);
  }

  .panel-header {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    justify-content: space-between;
    gap: 0.5rem;
  }

  h2,
  h3,
  p {
    margin: 0;
  }

  h2 {
    font-size: 1.125rem;
  }

  h3 {
    font-size: 1rem;
  }

  .paper-mark {
    padding: 0.125rem 0.375rem;
    border-radius: 0.25rem;
    background: var(--color-warning);
    color: var(--color-surface);
    font-size: 0.75rem;
    letter-spacing: 0.05em;
  }

  .live-status {
    color: var(--color-warning);
    font-size: 0.875rem;
  }

  .check-title {
    font-weight: 600;
  }

  .check-failed {
    color: var(--color-warning);
  }

  .check-detail {
    font-size: 0.875rem;
  }

  .balance {
    display: flex;
    flex-wrap: wrap;
    gap: 1.5rem;
    margin: 0;
  }

  .balance-currency {
    margin: 0;
    color: var(--color-muted);
    font-size: 0.875rem;
  }

  .balance-failed {
    color: var(--color-warning);
  }

  .balance dt {
    color: var(--color-muted);
    font-size: 0.875rem;
  }

  .balance dd {
    margin: 0;
    font-size: 1.25rem;
    font-variant-numeric: tabular-nums;
  }

  .positions {
    border-collapse: collapse;
    inline-size: 100%;
    font-size: 0.875rem;
  }

  .positions th,
  .positions td {
    padding: 0.375rem 0.75rem;
    border-bottom: 1px solid var(--color-border);
    text-align: start;
  }

  .positions thead th {
    position: sticky;
    inset-block-start: 0;
    background: var(--color-surface);
  }

  .positions .number {
    text-align: end;
    font-variant-numeric: tabular-nums;
  }
</style>
