<!-- The paper order panel of the instrument page (#103), IBKR Desktop layout: the Buy / Sell switch, the order fields
     in two columns, the order and account numbers in two columns, and the full-width button at the bottom. The order
     is for the instrument of the page, so the panel has no instrument fields. The limit price starts with the last
     price. A confirmation dialog with the PAPER mark comes before each order. A failed paper account check or a forward
     test on the instrument disables the button, and the panel says why. ATrade sends paper orders only. -->
<script lang="ts">
  import { Button, ContentSwitcher, Dialog, InlineNotification, Select, Tag, TextInput, type NotificationMessage } from '#lib/foundation/carbon';
  import { LiveUpdatesNotification } from '#lib/foundation/live_socket';
  import { ScrollRegion } from '#lib/foundation/scroll_region';
  import { ChangeText, formatPrice, formatSignedNumber } from '#lib/foundation/value_format';
  import {
    computeOrderValue,
    findInstrumentOrderBlock,
    findInstrumentPosition,
    formatStartLimitPrice,
    type OrderInstrument,
  } from './instrument_order';
  import { formatAmount, type PaperAccountMessage } from './paper_account';
  import {
    describeOrderForConfirmation,
    describeOrderTitle,
    readOrderForm,
    sendPaperOrder,
    type BlockingForwardTest,
    type OrderForm,
    type SendOrderRequest,
  } from './paper_orders';

  interface Props {
    instrument: OrderInstrument;
    /** The last price of the instrument. The limit price starts with it. */
    lastPrice: number | null;
    account: PaperAccountMessage | null;
    blockingForwardTests?: readonly BlockingForwardTest[];
    /** False while a live socket of the account or of the forward tests is not connected. */
    isConnected: boolean;
  }

  const { instrument, lastPrice, account, blockingForwardTests = [], isConnected }: Props = $props();

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

  const uid = $props.id();
  const blockReasonId = `order-block-${uid}`;

  const form = $state<Omit<OrderForm, keyof OrderInstrument>>({
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

  // A new instrument starts with an empty limit price, and the last price fills an empty limit price once. A new bar
  // period of the same instrument keeps the edits of the user.
  const instrumentKey = $derived(`${instrument.symbol}/${instrument.exchange}/${instrument.currency}`);
  let limitPriceInstrumentKey = '';
  let isLimitPriceFilled = false;
  $effect(() => {
    if (limitPriceInstrumentKey !== instrumentKey) {
      limitPriceInstrumentKey = instrumentKey;
      isLimitPriceFilled = false;
      form.limitPrice = '';
    }
    if (!isLimitPriceFilled && lastPrice !== null) {
      isLimitPriceFilled = true;
      form.limitPrice = formatStartLimitPrice(lastPrice);
    }
  });

  const accountId = $derived(account?.check.status === 'passed' ? (account.check.actual_accounts[0] ?? null) : null);
  const blockReason = $derived(findInstrumentOrderBlock(account, instrument, blockingForwardTests));
  const position = $derived(findInstrumentPosition(account, instrument));
  const unrealizedPnl = $derived(position === null ? null : Number(position.unrealized_pnl));
  const orderValue = $derived(computeOrderValue(form, lastPrice));
  const isBuy = $derived(form.side === 'BUY');

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

<ScrollRegion label="Paper order form" fill stretchContent>
  <form class="order-panel" aria-label="Paper order" onsubmit={reviewOrder}>
    <div class="fields">
      <LiveUpdatesNotification {isConnected} />
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
        <dd><ChangeText value={unrealizedPnl} text={formatSignedNumber(unrealizedPnl)} /></dd>
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
        kind={isBuy ? 'primary' : 'danger'}
        class="submit-button"
        bind:ref={reviewButton}
        disabled={blockReason !== null}
        aria-describedby={blockReason === null ? undefined : blockReasonId}
      >
        {isBuy ? 'Review buy order' : 'Review sell order'}
      </Button>
    </div>
  </form>
</ScrollRegion>

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
  /* The fields at the top and the button at the bottom. The numbers take the space between them. When the column is
     too low, the whole panel scrolls in its scroll region. */
  .order-panel {
    display: flex;
    flex: 1;
    flex-direction: column;
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

  .order-panel :global(input.number) {
    font-variant-numeric: tabular-nums;
    text-align: end;
  }

  .key-numbers {
    display: grid;
    flex: 1;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    align-content: start;
    margin: 0;
    padding: 0 var(--cds-spacing-05);
    border-block-start: 1px solid var(--cds-border-subtle-01);
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
    overflow-wrap: anywhere;
  }
</style>
