<!-- Order form for paper orders by hand. A confirmation dialog with the PAPER mark comes before each order. -->
<script lang="ts">
  import { InlineNotification } from '#lib/foundation/carbon';
  import {
    describeOrderForConfirmation,
    readOrderForm,
    sendPaperOrder,
    type OrderForm,
    type SendOrderRequest,
  } from './paper_orders';

  interface Props {
    // The checked paper account. The backend checks it again before it sends the order.
    accountId: string;
  }

  const { accountId }: Props = $props();

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
  let resultMessage = $state<{ title: string; subtitle?: string; isError: boolean } | null>(null);
  let reviewedRequest = $state<SendOrderRequest | null>(null);
  let isSending = $state(false);
  let dialog: HTMLDialogElement | undefined = $state();

  const confirmationLines = $derived(
    reviewedRequest === null ? [] : describeOrderForConfirmation(reviewedRequest, accountId),
  );

  function reviewOrder(event: SubmitEvent): void {
    event.preventDefault();
    resultMessage = null;
    const result = readOrderForm(form);
    if (result.kind === 'invalid') {
      formMessage = result.message;
      return;
    }
    formMessage = null;
    reviewedRequest = result.request;
    dialog?.showModal();
  }

  function closeDialog(): void {
    dialog?.close();
    reviewedRequest = null;
  }

  async function sendReviewedOrder(): Promise<void> {
    if (reviewedRequest === null) {
      return;
    }
    isSending = true;
    const result = await sendPaperOrder(fetch, reviewedRequest);
    isSending = false;
    closeDialog();
    if (result.kind === 'sent') {
      resultMessage = { title: `Order ${String(result.ibkrOrderId)} sent`, isError: false };
    } else {
      resultMessage = { title: 'Order not sent', subtitle: result.message, isError: true };
    }
  }
</script>

<form class="order-ticket" aria-label="Paper order" onsubmit={reviewOrder}>
  <label>
    Order symbol
    <input name="symbol" autocomplete="off" placeholder="AAPL" bind:value={form.symbol} />
  </label>
  <label>
    Exchange
    <input name="exchange" autocomplete="off" placeholder="NASDAQ" bind:value={form.exchange} />
  </label>
  <label>
    Currency
    <input name="currency" autocomplete="off" bind:value={form.currency} />
  </label>
  <label>
    Side
    <select name="side" bind:value={form.side}>
      <option value="BUY">Buy</option>
      <option value="SELL">Sell</option>
    </select>
  </label>
  <label>
    Quantity
    <input name="quantity" inputmode="numeric" bind:value={form.quantity} />
  </label>
  <label>
    Order type
    <select name="order_type" bind:value={form.orderType}>
      <option value="LMT">Limit</option>
      <option value="MKT">Market</option>
    </select>
  </label>
  {#if form.orderType === 'LMT'}
    <label>
      Limit price
      <input name="limit_price" inputmode="decimal" bind:value={form.limitPrice} />
    </label>
  {/if}
  <label>
    Time in force
    <select name="time_in_force" bind:value={form.timeInForce}>
      <option value="DAY">DAY</option>
      <option value="GTC">GTC</option>
    </select>
  </label>
  <button type="submit">Review order</button>
</form>

{#if formMessage !== null}
  <p class="message error" role="alert">{formMessage}</p>
{/if}
{#if resultMessage !== null}
  <InlineNotification
    kind={resultMessage.isError ? 'error' : 'success'}
    title={resultMessage.title}
    subtitle={resultMessage.subtitle}
    lowContrast
    onClose={() => (resultMessage = null)}
  />
{/if}

<dialog bind:this={dialog} aria-labelledby="confirm-order-title" oncancel={closeDialog}>
  <h3 id="confirm-order-title">Confirm paper order</h3>
  <p class="paper-mark">PAPER</p>
  <dl class="confirmation">
    {#each confirmationLines as line (line.label)}
      <div>
        <dt>{line.label}</dt>
        <dd>{line.value}</dd>
      </div>
    {/each}
  </dl>
  <div class="dialog-buttons">
    <button type="button" onclick={closeDialog} disabled={isSending}>Back</button>
    <button type="button" class="send" onclick={sendReviewedOrder} disabled={isSending}>Send paper order</button>
  </div>
</dialog>

<style>
  .order-ticket {
    display: flex;
    flex-wrap: wrap;
    align-items: end;
    gap: 0.5rem 0.75rem;
  }

  .order-ticket label {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    font-size: 0.875rem;
  }

  .order-ticket input {
    inline-size: 7rem;
  }

  .message {
    margin: 0;
    font-size: 0.875rem;
  }

  .error {
    color: var(--color-warning);
    font-weight: 600;
  }

  dialog {
    max-inline-size: min(28rem, calc(100vw - 2rem));
    border: 1px solid var(--color-border);
    border-radius: 0.5rem;
    background: var(--color-surface);
    color: inherit;
  }

  h3 {
    margin: 0 0 0.5rem;
    font-size: 1rem;
  }

  .paper-mark {
    display: inline-block;
    margin: 0 0 0.75rem;
    padding: 0.125rem 0.5rem;
    border-radius: 0.25rem;
    background: var(--color-warning);
    color: var(--color-surface);
    font-weight: 700;
    letter-spacing: 0.1em;
  }

  .confirmation {
    display: grid;
    gap: 0.375rem;
    margin: 0 0 1rem;
  }

  .confirmation div {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
  }

  .confirmation dt {
    color: var(--color-muted);
  }

  .confirmation dd {
    margin: 0;
    font-variant-numeric: tabular-nums;
    overflow-wrap: anywhere;
  }

  .dialog-buttons {
    display: flex;
    justify-content: end;
    gap: 0.5rem;
  }

  .send {
    font-weight: 600;
  }
</style>
