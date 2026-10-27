// Paper orders by hand: checks the order form, writes the confirmation text, and calls the order routes.
// The order list comes from the "orders" message of /ws/paper-trading (docs/architecture/paper_trading.md).
import type { components } from '#lib/api';
import { describeErrorBody, readJsonBody, sendRequest } from '#lib/foundation/http_request';
import { readSocketMessage } from '#lib/foundation/live_socket';

export type SendOrderRequest = components['schemas']['SendOrderRequest'];
export type OpenOrder = components['schemas']['OpenOrderResponse'];
export type OrderSource = components['schemas']['OrderSourceResponse'];
export type ManualOrder = components['schemas']['ManualOrderWithFillsResponse'];
type OrderSide = components['schemas']['OrderSide'];
type OrderType = components['schemas']['OrderType'];
type TimeInForce = components['schemas']['TimeInForce'];
type OpenOrdersMessage = components['schemas']['OpenOrdersMessage'];
type OrderRefusedResponse = components['schemas']['OrderRefusedResponse'];

// The text of the form fields, before the check.
export interface OrderForm {
  symbol: string;
  exchange: string;
  currency: string;
  side: OrderSide;
  quantity: string;
  orderType: OrderType;
  limitPrice: string;
  timeInForce: TimeInForce;
}

export type OrderFormResult = { kind: 'valid'; request: SendOrderRequest } | { kind: 'invalid'; message: string };
export type SendOrderResult = { kind: 'sent'; ibkrOrderId: number } | { kind: 'failed'; message: string };
export type CancelOrderResult = { kind: 'cancel_sent' } | { kind: 'failed'; message: string };

export interface ConfirmationLine {
  label: string;
  value: string;
}

export const PAPER_ORDERS_PATH = '/api/paper-trading/orders';
const MANUAL_ORDERS_PATH = '/api/paper-trading/manual-orders';

const WHOLE_NUMBER_PATTERN = /^\d+$/;
const SIDE_NAMES: Record<OrderSide, string> = { BUY: 'Buy', SELL: 'Sell' };
const ORDER_TYPE_NAMES: Record<OrderType, string> = { MKT: 'Market', LMT: 'Limit' };

export function readOrderForm(form: OrderForm): OrderFormResult {
  const symbol = form.symbol.trim().toUpperCase();
  const exchange = form.exchange.trim().toUpperCase();
  const currency = form.currency.trim().toUpperCase();
  if (symbol === '' || exchange === '' || currency === '') {
    return { kind: 'invalid', message: 'Enter the symbol, the exchange, and the currency.' };
  }
  const quantityText = form.quantity.trim();
  const quantity = Number(quantityText);
  if (!WHOLE_NUMBER_PATTERN.test(quantityText) || quantity <= 0) {
    return { kind: 'invalid', message: 'The quantity must be a whole number larger than 0.' };
  }
  let limitPrice: string | null = null;
  if (form.orderType === 'LMT') {
    limitPrice = form.limitPrice.trim();
    if (limitPrice === '' || !(Number(limitPrice) > 0)) {
      return { kind: 'invalid', message: 'A limit order needs a limit price larger than 0.' };
    }
  }
  return {
    kind: 'valid',
    request: {
      symbol,
      exchange,
      currency,
      side: form.side,
      quantity,
      order_type: form.orderType,
      limit_price: limitPrice,
      time_in_force: form.timeInForce,
    },
  };
}

export function describeOrderForConfirmation(request: SendOrderRequest, accountId: string): ConfirmationLine[] {
  const price = request.limit_price === null ? 'Market price' : String(request.limit_price);
  return [
    { label: 'Instrument', value: `${request.symbol} / ${request.exchange} / ${request.currency}` },
    { label: 'Side', value: SIDE_NAMES[request.side] },
    { label: 'Quantity', value: String(request.quantity) },
    { label: 'Order type', value: `${ORDER_TYPE_NAMES[request.order_type]}, ${request.time_in_force}` },
    { label: 'Price', value: price },
    { label: 'Account', value: accountId },
  ];
}

export function describeOrderSource(source: OrderSource): string {
  if (source.kind === 'forward_test') {
    return `forward test ${String(source.forward_test_id)}`;
  }
  return 'by hand';
}

export function readOpenOrdersMessage(message: unknown): OpenOrder[] | null {
  return readSocketMessage<OpenOrdersMessage>(message, ['orders'])?.orders ?? null;
}

export async function sendPaperOrder(fetchFunction: typeof fetch, request: SendOrderRequest): Promise<SendOrderResult> {
  const response = await sendRequest(fetchFunction, PAPER_ORDERS_PATH, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (response === null) {
    return { kind: 'failed', message: 'Backend not reachable. ATrade did not send the order.' };
  }
  if (!response.ok) {
    const message = describeOrderError(await readJsonBody(response), response.status, 'The order request');
    return { kind: 'failed', message: `ATrade did not send the order. ${message}` };
  }
  const sentOrder = (await response.json()) as components['schemas']['ManualOrderResponse'];
  return { kind: 'sent', ibkrOrderId: sentOrder.ibkr_order_id };
}

export async function cancelPaperOrder(fetchFunction: typeof fetch, orderId: number): Promise<CancelOrderResult> {
  const response = await sendRequest(fetchFunction, `${PAPER_ORDERS_PATH}/${String(orderId)}`, { method: 'DELETE' });
  if (response === null) {
    return { kind: 'failed', message: 'Backend not reachable. ATrade did not cancel the order.' };
  }
  if (!response.ok) {
    return {
      kind: 'failed',
      message: describeOrderError(await readJsonBody(response), response.status, 'The cancel request'),
    };
  }
  return { kind: 'cancel_sent' };
}

function isFilled(order: ManualOrder): boolean {
  return order.filled_quantity !== null && Number(order.filled_quantity) > 0;
}

/** The orders by hand with a fill from IBKR, newest first. Null when the backend does not answer. */
export async function readFilledManualOrders(fetchFunction: typeof fetch): Promise<ManualOrder[] | null> {
  const response = await sendRequest(fetchFunction, MANUAL_ORDERS_PATH);
  if (response === null || !response.ok) {
    return null;
  }
  const body = (await response.json()) as components['schemas']['ManualOrderListResponse'];
  return body.manual_orders.filter(isFilled).reverse();
}

function isRefusedOrder(body: unknown): body is OrderRefusedResponse {
  return typeof body === 'object' && body !== null && 'actual_accounts' in body && 'expected_account' in body;
}

// A refused order (403) has the actual and the expected account. Other errors have only {"detail": "<message>"}.
function describeOrderError(body: unknown, status: number, failedAction: string): string {
  const message = describeErrorBody(body, status, failedAction);
  if (!isRefusedOrder(body) || typeof body.detail !== 'string' || !Array.isArray(body.actual_accounts)) {
    return message;
  }
  const actualAccounts = body.actual_accounts.length > 0 ? body.actual_accounts.join(', ') : 'none';
  const expectedAccount = body.expected_account ?? 'not set';
  return `${message} Actual account: ${actualAccounts}. Expected account: ${expectedAccount}.`;
}
