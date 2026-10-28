<!-- PROTOTYPE (#99), throwaway: the paper order panel of the instrument workbench, IBKR Desktop layout: side switch,
     order fields, key numbers in two columns, and the button at the bottom. The order is for the instrument of the page.
     A confirmation dialog with the PAPER mark comes before each order, as in PaperOrderTicket. -->
<script lang="ts">
  import { Button, ContentSwitcher, Dialog, InlineNotification, Select, Tag, TextInput, type NotificationMessage } from '#lib/foundation/carbon';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import type { Instrument } from '#lib/market_data';
  import {
    describeOrderForConfirmation,
    describeOrderTitle,
    describePaperAccountCheck,
    formatAmount,
    readOrderForm,
    sendPaperOrder,
    type OrderForm,
    type PaperAccountMessage,
    type SendOrderRequest,
  } from '#lib/paper_trading';
  import { findAmountDirection, formatPrice, formatSignedAmount } from './instrument_quote';

  interface Props {
    instrument: Instrument;
    lastPrice: number | null;
    account: PaperAccountMessage | null;
  }

  const { instrument, lastPrice, account }: Props = $props();

  const SIDES = [
    { value: 'BUY' as const, label: 'Buy' },
    { value: 'SELL' as const, label: 'Sell' },
  ];
  const ORDER_TYPES = [
    { value: 'LMT' as const, label: 'Limit' },
    { value: 'MKT' as const, label: 'Market' },
  ];
  const TIMES_IN_FORCE = [
    { value: 'DAY' as const, label: 'DAY' },
    { value: 'GTC' as const, label: 'GTC' },
  ];

  const PRICE_DECIMALS = 2;

  const uid = $props.id();
  const blockReasonId = `order-block-${uid}`;

  const form = $state<Omit<OrderForm, 'symbol' | 'exchange' | 'currency'>>({
    side: 'BUY',
    quantity: '1',
    orderType: 'LMT',
    limitPrice: '',
    timeInForce: 'DAY',
  });
  let formMessage = $state<string | null>(null);
  let resultMessage = $state<NotificationMessage | null>(null);
  let reviewedRequest = $state<SendOrderRequest | null>(null);
  let isDialogOpen = $state(false);
  let isSending = $state(false);
  let reviewButton: HTMLButtonElement | null = $state(null);

  // A new instrument starts with an empty limit price. The last price fills it.
  let limitPriceInstrument = '';
  $effect(() => {
    const instrumentKey = `${instrument.symbol}/${instrument.exchange}/${instrument.currency}`;
    if (limitPriceInstrument !== instrumentKey) {
      limitPriceInstrument = instrumentKey;
      form.limitPrice = '';
    }
    if (form.limitPrice === '' && lastPrice !== null) {
      form.limitPrice = lastPrice.toFixed(PRICE_DECIMALS);
    }
  });

  const accountId = $derived(
    account?.check.status === 'passed' ? (account.check.actual_accounts[0] ?? null) : null,
  );
  const blockReason = $derived.by(() => {
    if (account === null) {
      return 'Reading the paper account.';
    }
    return accountId === null ? describePaperAccountCheck(account.check).title : null;
  });

  const position = $derived(
    account?.positions.find(
      (candidate) => candidate.symbol === instrument.symbol && candidate.exchange === instrument.exchange,
    ) ?? null,
  );

  const orderValue = $derived.by(() => {
    const quantity = Number(form.quantity);
    const price = form.orderType === 'LMT' ? Number(form.limitPrice) : lastPrice;
    if (!Number.isFinite(quantity) || price === null || !Number.isFinite(price) || form.quantity.trim() === '') {
      return null;
    }
    return quantity * price;
  });

  function reviewOrder(event: SubmitEvent): void {
    event.preventDefault();
    if (blockReason !== null) {
      return;
    }
    resultMessage = null;
    const result = readOrderForm({ ...form, ...instrument });
    if (result.kind === 'invalid') {
      formMessage = result.message;
      return;
    }
    formMessage = null;
    reviewedRequest = result.request;
    isDialogOpen = true;
  }

  async function sendReviewedOrder(): Promise<void> {
    if (reviewedRequest === null) {
      return;
    }
    isSending = true;
    const result = await sendPaperOrder(fetch, reviewedRequest);
    isSending = false;
    isDialogOpen = false;
    resultMessage =
      result.kind === 'sent'
        ? { kind: 'success', title: `Order ${String(result.ibkrOrderId)} sent` }
        : { kind: 'error', title: 'Order not sent', subtitle: result.message };
  }
</script>

<form class="order-panel" aria-label="Paper order" onsubmit={reviewOrder}>
  <div class="fields">
    <ContentSwitcher
      label="Side"
      items={SIDES}
      value={form.side}
      onValueChange={(side: OrderForm['side']) => {
        form.side = side;
      }}
    />
    <div class="field-pair">
      <TextInput label="Quantity" name="quantity" inputmode="numeric" class="number" bind:value={form.quantity} />
      <Select
        label="Order type"
        items={ORDER_TYPES}
        value={form.orderType}
        onValueChange={(orderType: OrderForm['orderType']) => {
          form.orderType = orderType;
        }}
      />
    </div>
    <div class="field-pair">
      {#if form.orderType === 'LMT'}
        <TextInput label="Limit price" name="limit_price" inputmode="decimal" class="number" bind:value={form.limitPrice} />
      {:else}
        <div></div>
      {/if}
      <Select
        label="Time in force"
        items={TIMES_IN_FORCE}
        value={form.timeInForce}
        onValueChange={(timeInForce: OrderForm['timeInForce']) => {
          form.timeInForce = timeInForce;
        }}
      />
    </div>
  </div>

  <ScrollRegion label="Order and account numbers" maxHeight="100%">
  <dl class="key-numbers">
    <div>
      <dt>Order value</dt>
      <dd>{formatPrice(orderValue)}</dd>
    </div>
    <div>
      <dt>Position</dt>
      <dd>{position?.quantity ?? '0'}</dd>
    </div>
    <div>
      <dt>Average cost</dt>
      <dd>{formatAmount(position?.average_cost ?? null)}</dd>
    </div>
    <div>
      <dt>Unrealized P&L</dt>
      <dd class={`signed--${findAmountDirection(position?.unrealized_pnl ?? null)}`}>
        {formatSignedAmount(position?.unrealized_pnl ?? null)}
      </dd>
    </div>
    <div>
      <dt>Cash (USD)</dt>
      <dd>{formatAmount(account?.balance?.cash_usd ?? null)}</dd>
    </div>
    <div>
      <dt>Net liquidation (USD)</dt>
      <dd>{formatAmount(account?.balance?.net_liquidation_usd ?? null)}</dd>
    </div>
  </dl>
  </ScrollRegion>

  <div class="submit">
    {#if blockReason !== null}
      <p id={blockReasonId} class="message">{blockReason}</p>
    {/if}
    {#if formMessage !== null}
      <p class="message message--error" role="alert">{formMessage}</p>
    {/if}
    {#if resultMessage !== null}
      <InlineNotification {...resultMessage} lowContrast onClose={() => (resultMessage = null)} />
    {/if}
    <Button
      type="submit"
      kind={form.side === 'BUY' ? 'primary' : 'danger'}
      size="lg"
      class="submit-button"
      bind:ref={reviewButton}
      disabled={blockReason !== null}
      aria-describedby={blockReason === null ? undefined : blockReasonId}
    >
      {form.side === 'BUY' ? 'Review buy order' : 'Review sell order'}
    </Button>
  </div>
</form>

{#if reviewedRequest !== null && accountId !== null}
  <Dialog
    open={isDialogOpen}
    onOpenChange={(open: boolean) => {
      isDialogOpen = open;
    }}
    label={accountId}
    title={describeOrderTitle(reviewedRequest)}
    primaryText="Send paper order"
    primaryKind={reviewedRequest.side === 'BUY' ? 'primary' : 'danger'}
    busy={isSending}
    returnFocus={reviewButton}
    onPrimary={() => {
      void sendReviewedOrder();
    }}
  >
    <Tag label="PAPER" kind="blue" />
    <dl class="confirmation">
      {#each describeOrderForConfirmation(reviewedRequest) as line (line.label)}
        <div>
          <dt>{line.label}</dt>
          <dd>{line.value}</dd>
        </div>
      {/each}
    </dl>
  </Dialog>
{/if}

<style>
  /* Fields at the top, the button at the bottom. The numbers fill the space between them. */
  .order-panel {
    display: grid;
    grid-template-rows: auto minmax(0, 1fr) auto;
    block-size: 100%;
  }

  .fields {
    display: flex;
    flex-direction: column;
    gap: var(--cds-spacing-05);
    padding: var(--cds-spacing-05);
  }

  .field-pair {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: var(--cds-spacing-05);
    align-items: end;
  }

  .order-panel > :global(.scroll-region) {
    border-block-start: 1px solid var(--cds-border-subtle-01);
  }

  .order-panel :global(input.number) {
    font-variant-numeric: tabular-nums;
    text-align: end;
  }

  .key-numbers {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    align-content: start;
    margin: 0;
    padding: 0 var(--cds-spacing-05);
  }

  .key-numbers div {
    padding-block: var(--cds-spacing-03);
    border-block-end: 1px solid var(--cds-border-subtle-01);
  }

  .key-numbers div:nth-child(odd) {
    padding-inline-end: var(--cds-spacing-03);
  }

  .key-numbers div:nth-child(even) {
    padding-inline-start: var(--cds-spacing-03);
  }

  .key-numbers dt {
    font-size: var(--cds-label-01-font-size);
    line-height: var(--cds-label-01-line-height);
    letter-spacing: var(--cds-label-01-letter-spacing);
    color: var(--cds-text-secondary);
  }

  .key-numbers dd {
    margin: 0;
    text-align: end;
    font-size: var(--cds-body-compact-02-font-size);
    line-height: var(--cds-body-compact-02-line-height);
    font-variant-numeric: tabular-nums;
  }

  .signed--up {
    color: var(--cds-support-success);
  }

  .signed--down {
    color: var(--cds-support-error);
  }

  .submit {
    display: flex;
    flex-direction: column;
    gap: var(--cds-spacing-03);
    padding: var(--cds-spacing-05);
  }

  .submit :global(.submit-button) {
    inline-size: 100%;
    max-inline-size: none;
  }

  .message {
    margin: 0;
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
    letter-spacing: var(--cds-body-compact-01-letter-spacing);
    color: var(--cds-text-secondary);
  }

  .message--error {
    color: var(--cds-text-error);
  }

  .confirmation {
    display: grid;
    margin: var(--cds-spacing-05) 0 0;
  }

  .confirmation div {
    display: flex;
    justify-content: space-between;
    gap: var(--cds-spacing-05);
    padding-block: var(--cds-spacing-03);
    border-block-end: 1px solid var(--cds-border-subtle-01);
  }

  .confirmation dt {
    color: var(--cds-text-secondary);
  }

  .confirmation dd {
    margin: 0;
    font-variant-numeric: tabular-nums;
  }
</style>
