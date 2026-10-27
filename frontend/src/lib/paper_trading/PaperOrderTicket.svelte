<!-- Order form for paper orders by hand. A confirmation dialog with the PAPER mark comes before each order. A forward
     test that trades the instrument of the form disables the form button, and the form says why. -->
<script lang="ts">
  import { Button, ContentSwitcher, Dialog, InlineNotification, Select, Tag, TextInput, type NotificationMessage } from '#lib/foundation/carbon';
  import {
    describeOrderForConfirmation,
    describeOrderTitle,
    findOrderBlock,
    readOrderForm,
    sendPaperOrder,
    type BlockingForwardTest,
    type OrderForm,
    type SendOrderRequest,
  } from './paper_orders';

  interface Props {
    // The checked paper account. The backend checks it again before it sends the order.
    accountId: string;
    blockingForwardTests?: readonly BlockingForwardTest[];
  }

  const { accountId, blockingForwardTests = [] }: Props = $props();

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

  const form = $state<OrderForm>({
    symbol: '',
    exchange: '',
    currency: 'USD',
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

  const blockReason = $derived(findOrderBlock(form, blockingForwardTests));

  function reviewOrder(event: SubmitEvent): void {
    event.preventDefault();
    if (blockReason !== null) {
      return;
    }
    resultMessage = null;
    const result = readOrderForm(form);
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
    if (result.kind === 'sent') {
      resultMessage = { kind: 'success', title: `Order ${String(result.ibkrOrderId)} sent` };
    } else {
      resultMessage = { kind: 'error', title: 'Order not sent', subtitle: result.message };
    }
  }
</script>

<form class="order-ticket atrade-auto-grid atrade-auto-grid--narrow" aria-label="Paper order" onsubmit={reviewOrder}>
  <div class="side">
    <ContentSwitcher
      label="Side"
      items={SIDES}
      value={form.side}
      onValueChange={(side: OrderForm['side']) => {
        form.side = side;
      }}
    />
  </div>
  <TextInput label="Order symbol" name="symbol" autocomplete="off" placeholder="AAPL" bind:value={form.symbol} />
  <TextInput label="Exchange" name="exchange" autocomplete="off" placeholder="NASDAQ" bind:value={form.exchange} />
  <TextInput label="Currency" name="currency" autocomplete="off" bind:value={form.currency} />
  <TextInput label="Quantity" name="quantity" inputmode="numeric" class="number" bind:value={form.quantity} />
  <Select
    label="Order type"
    items={ORDER_TYPES}
    value={form.orderType}
    onValueChange={(orderType: OrderForm['orderType']) => {
      form.orderType = orderType;
    }}
  />
  {#if form.orderType === 'LMT'}
    <TextInput label="Limit price" name="limit_price" inputmode="decimal" class="number" bind:value={form.limitPrice} />
  {/if}
  <Select
    label="Time in force"
    items={TIMES_IN_FORCE}
    value={form.timeInForce}
    onValueChange={(timeInForce: OrderForm['timeInForce']) => {
      form.timeInForce = timeInForce;
    }}
  />
  <div class="submit">
    <Button
      type="submit"
      bind:ref={reviewButton}
      disabled={blockReason !== null}
      aria-describedby={blockReason === null ? undefined : blockReasonId}
    >
      Review order
    </Button>
  </div>
</form>

{#if blockReason !== null}
  <p id={blockReasonId} class="message">{blockReason}</p>
{/if}
{#if formMessage !== null}
  <p class="message error" role="alert">{formMessage}</p>
{/if}
{#if resultMessage !== null}
  <InlineNotification
    {...resultMessage}
    lowContrast
    onClose={() => (resultMessage = null)}
  />
{/if}

{#if reviewedRequest !== null}
  <Dialog
    open={isDialogOpen}
    onOpenChange={(open: boolean) => {
      isDialogOpen = open;
    }}
    label={accountId}
    title={describeOrderTitle(reviewedRequest)}
    primaryText="Send paper order"
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
  .order-ticket {
    align-items: end;
  }

  .side,
  .submit {
    grid-column: 1 / -1;
  }

  .order-ticket :global(input.number) {
    font-variant-numeric: tabular-nums;
    text-align: end;
  }

  .message {
    margin: 0;
    font-size: var(--cds-body-compact-01-font-size);
    line-height: var(--cds-body-compact-01-line-height);
    letter-spacing: var(--cds-body-compact-01-letter-spacing);
    color: var(--cds-text-secondary);
  }

  .error {
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
