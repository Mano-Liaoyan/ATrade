<!-- Account panel: the paper account check, the balance, the positions, the order form, and the open orders,
     updated live from /ws/paper-trading. -->
<script lang="ts">
  import { StatusIndicator, Tag } from '#lib/foundation/carbon';
  import { LiveUpdatesNotification } from '#lib/foundation/live_socket';
  import {
    describeBalanceCurrency,
    describePaperAccountCheck,
    findPaperAccountCheckKind,
    formatAmount,
  } from './paper_account';
  import FilledManualOrderList from './FilledManualOrderList.svelte';
  import OpenOrderList from './OpenOrderList.svelte';
  import { PaperAccountFeed } from './paper_account_feed.svelte';
  import type { BlockingForwardTest } from './paper_orders';
  import PaperOrderTicket from './PaperOrderTicket.svelte';
  import PositionTable from './PositionTable.svelte';

  interface Props {
    // The forward tests that block orders by hand on their instruments.
    blockingForwardTests?: readonly BlockingForwardTest[];
  }

  const { blockingForwardTests = [] }: Props = $props();

  const feed = new PaperAccountFeed();
  $effect(() => feed.start(fetch, window.location));

  const checkDescription = $derived(feed.account === null ? null : describePaperAccountCheck(feed.account.check));
</script>

<section class="account-panel" aria-labelledby="account-panel-title">
  <h2 id="account-panel-title">Paper account <Tag label="PAPER" kind="red" size="sm" /></h2>
  <LiveUpdatesNotification isConnected={feed.isConnected} />

  {#if feed.account === null || checkDescription === null}
    <p role="status" aria-label="Paper account check">
      <StatusIndicator kind="in-progress" label="Reading the paper account." />
    </p>
  {:else}
    {@const account = feed.account}
    <div role="status" aria-label="Paper account check">
      <StatusIndicator kind={findPaperAccountCheckKind(account.check.status)} label={checkDescription.title} />
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
      <PositionTable positions={account.positions} />
    {/if}

    {#if account.check.status === 'passed' && account.check.actual_accounts[0] !== undefined}
      <h3>New paper order</h3>
      <PaperOrderTicket accountId={account.check.actual_accounts[0]} {blockingForwardTests} />
    {/if}

    <h3>Open orders</h3>
    <OpenOrderList orders={feed.openOrders} />

    <h3>Filled orders by hand</h3>
    <FilledManualOrderList orders={feed.filledOrders} />
  {/if}
</section>

<style>
  .account-panel {
    display: flex;
    flex-direction: column;
    gap: var(--cds-spacing-05);
    max-inline-size: 60rem;
    margin-block-start: var(--cds-spacing-07);
  }

  h2 {
    display: flex;
    align-items: center;
    gap: var(--cds-spacing-03);
    font-size: var(--cds-heading-compact-02-font-size);
    font-weight: var(--cds-heading-compact-02-font-weight);
    line-height: var(--cds-heading-compact-02-line-height);
    letter-spacing: var(--cds-heading-compact-02-letter-spacing);
  }

  h3 {
    margin-block-start: var(--cds-spacing-05);
    font-size: var(--cds-heading-compact-01-font-size);
    font-weight: var(--cds-heading-compact-01-font-weight);
    line-height: var(--cds-heading-compact-01-line-height);
    letter-spacing: var(--cds-heading-compact-01-letter-spacing);
  }

  p {
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
    letter-spacing: var(--cds-body-compact-01-letter-spacing);
  }

  .check-detail {
    margin-block-start: var(--cds-spacing-02);
  }

  .balance {
    display: flex;
    flex-wrap: wrap;
    gap: var(--cds-spacing-07);
  }

  .balance dt {
    margin-block-end: var(--cds-spacing-02);
    font-size: var(--cds-label-01-font-size);
    line-height: var(--cds-label-01-line-height);
    letter-spacing: var(--cds-label-01-letter-spacing);
    color: var(--cds-text-secondary);
  }

  .balance dd {
    font-size: var(--cds-heading-03-font-size);
    font-weight: var(--cds-heading-03-font-weight);
    line-height: var(--cds-heading-03-line-height);
    font-variant-numeric: tabular-nums;
  }

  .balance-currency {
    font-size: var(--cds-helper-text-01-font-size);
    line-height: var(--cds-helper-text-01-line-height);
    letter-spacing: var(--cds-helper-text-01-letter-spacing);
    color: var(--cds-text-secondary);
  }

  .balance-failed {
    color: var(--cds-text-error);
  }
</style>
