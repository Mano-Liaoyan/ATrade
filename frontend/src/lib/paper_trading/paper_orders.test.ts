// Paper orders by hand: the order form check, the confirmation text, the order source, and the HTTP calls.
import { describe, expect, it } from 'vite-plus/test';
import {
  cancelPaperOrder,
  describeCancelAction,
  describeOrderSource,
  describeOrderForConfirmation,
  describeOrderTitle,
  findOpenOrderStatusKind,
  readFilledManualOrders,
  readOpenOrdersMessage,
  readOrderForm,
  sendPaperOrder,
  type ManualOrder,
  type OrderForm,
} from './paper_orders';

const limitForm: OrderForm = {
  symbol: ' aapl ',
  exchange: 'NASDAQ',
  currency: 'USD',
  side: 'BUY',
  quantity: '3',
  orderType: 'LMT',
  limitPrice: '1.25',
  timeInForce: 'GTC',
};

function makeFetch(status: number, body: unknown, requests: Request[] = []): typeof fetch {
  return (input, init) => {
    requests.push(new Request(new URL(input as string, 'http://test'), init));
    return Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } }));
  };
}

describe('readOrderForm', () => {
  it('makes a limit order request with an upper-case symbol', () => {
    expect(readOrderForm(limitForm)).toEqual({
      kind: 'valid',
      request: {
        symbol: 'AAPL',
        exchange: 'NASDAQ',
        currency: 'USD',
        side: 'BUY',
        quantity: 3,
        order_type: 'LMT',
        limit_price: '1.25',
        time_in_force: 'GTC',
      },
    });
  });

  it('sends no limit price with a market order', () => {
    const result = readOrderForm({ ...limitForm, orderType: 'MKT', limitPrice: '1.25' });

    expect(result.kind === 'valid' && result.request.limit_price).toBeNull();
  });

  it.each([
    [{ symbol: '  ' }, 'Enter the symbol, the exchange, and the currency.'],
    [{ quantity: '0' }, 'The quantity must be a whole number larger than 0.'],
    [{ quantity: '1.5' }, 'The quantity must be a whole number larger than 0.'],
    [{ limitPrice: '' }, 'A limit order needs a limit price larger than 0.'],
    [{ limitPrice: '-2' }, 'A limit order needs a limit price larger than 0.'],
  ])('refuses %o', (changedFields, message) => {
    expect(readOrderForm({ ...limitForm, ...changedFields })).toEqual({ kind: 'invalid', message });
  });
});

describe('describeOrderForConfirmation', () => {
  it('lists the instrument, the order type, and the price', () => {
    const result = readOrderForm(limitForm);
    if (result.kind !== 'valid') {
      throw new Error('The form must be valid.');
    }

    expect(describeOrderForConfirmation(result.request)).toEqual([
      { label: 'Instrument', value: 'AAPL / NASDAQ / USD' },
      { label: 'Order type', value: 'Limit, GTC' },
      { label: 'Price', value: '1.25' },
    ]);
  });

  it('shows the market price for a market order', () => {
    const result = readOrderForm({ ...limitForm, side: 'SELL', orderType: 'MKT', timeInForce: 'DAY' });
    if (result.kind !== 'valid') {
      throw new Error('The form must be valid.');
    }

    const lines = describeOrderForConfirmation(result.request);

    expect(lines).toContainEqual({ label: 'Order type', value: 'Market, DAY' });
    expect(lines).toContainEqual({ label: 'Price', value: 'Market price' });
  });
});

describe('describeOrderTitle', () => {
  it('names the side, the quantity, and the symbol', () => {
    const result = readOrderForm({ ...limitForm, quantity: '50' });
    if (result.kind !== 'valid') {
      throw new Error('The form must be valid.');
    }

    expect(describeOrderTitle(result.request)).toBe('Buy 50 AAPL');
    expect(describeOrderTitle({ ...result.request, side: 'SELL' })).toBe('Sell 50 AAPL');
  });
});

describe('describeOrderSource', () => {
  it('names orders by hand and forward test orders', () => {
    expect(describeOrderSource({ kind: 'by_hand', forward_test_id: null })).toBe('by hand');
    expect(describeOrderSource({ kind: 'forward_test', forward_test_id: 42 })).toBe('forward test 42');
  });
});

describe('findOpenOrderStatusKind', () => {
  it.each([
    ['Submitted', 'in-progress'],
    ['PreSubmitted', 'in-progress'],
    ['PendingSubmit', 'in-progress'],
    ['PendingCancel', 'in-progress'],
    ['ApiPending', 'in-progress'],
    ['Filled', 'success'],
    ['Cancelled', 'neutral'],
    ['ApiCancelled', 'neutral'],
    ['Inactive', 'warning'],
    ['SomethingNew', 'neutral'],
  ])('gives the status icon kind of the IBKR order status %s', (status, kind) => {
    expect(findOpenOrderStatusKind(status)).toBe(kind);
  });
});

describe('describeCancelAction', () => {
  it('enables the cancel action of an order by hand that ATrade can cancel', () => {
    expect(describeCancelAction({ can_cancel: true, source: { kind: 'by_hand', forward_test_id: null } })).toEqual({
      label: 'Cancel order',
      disabled: false,
    });
  });

  it('disables the cancel action of a forward test order and says how to cancel it', () => {
    expect(describeCancelAction({ can_cancel: false, source: { kind: 'forward_test', forward_test_id: 42 } })).toEqual({
      label: 'Stop forward test 42 to cancel',
      disabled: true,
    });
  });

  it('disables the cancel action of an order that another IBKR client sent', () => {
    expect(describeCancelAction({ can_cancel: false, source: { kind: 'by_hand', forward_test_id: null } })).toEqual({
      label: 'Cancel order: sent by another IBKR client',
      disabled: true,
    });
  });
});

describe('readOpenOrdersMessage', () => {
  it('reads an orders message and ignores other messages', () => {
    expect(readOpenOrdersMessage({ type: 'orders', orders: [] })).toEqual([]);
    expect(readOpenOrdersMessage({ type: 'account' })).toBeNull();
    expect(readOpenOrdersMessage(null)).toBeNull();
  });
});

describe('sendPaperOrder', () => {
  it('posts the order and returns the IBKR order ID', async () => {
    const requests: Request[] = [];
    const result = readOrderForm(limitForm);
    if (result.kind !== 'valid') {
      throw new Error('The form must be valid.');
    }

    const sent = await sendPaperOrder(makeFetch(201, { ibkr_order_id: 1001 }, requests), result.request);

    expect(sent).toEqual({ kind: 'sent', ibkrOrderId: 1001 });
    expect(requests[0]?.method).toBe('POST');
    expect(new URL(requests[0]?.url ?? '').pathname).toBe('/api/paper-trading/orders');
    expect(await requests[0]?.json()).toEqual(result.request);
  });

  it('shows the actual and the expected account when the paper account check refuses the order', async () => {
    const result = readOrderForm(limitForm);
    if (result.kind !== 'valid') {
      throw new Error('The form must be valid.');
    }
    const body = { detail: 'Wrong account.', actual_accounts: ['DU7654321'], expected_account: 'DU1234567' };

    const sent = await sendPaperOrder(makeFetch(403, body), result.request);

    expect(sent).toEqual({
      kind: 'failed',
      message: 'ATrade did not send the order. Wrong account. Actual account: DU7654321. Expected account: DU1234567.',
    });
  });

  it('reports an unreachable backend', async () => {
    const result = readOrderForm(limitForm);
    if (result.kind !== 'valid') {
      throw new Error('The form must be valid.');
    }

    const sent = await sendPaperOrder(() => Promise.reject(new TypeError('offline')), result.request);

    expect(sent).toEqual({ kind: 'failed', message: 'Backend not reachable. ATrade did not send the order.' });
  });
});

describe('cancelPaperOrder', () => {
  it('sends DELETE for the order ID', async () => {
    const requests: Request[] = [];

    const cancelled = await cancelPaperOrder(makeFetch(202, null, requests), 1001);

    expect(cancelled).toEqual({ kind: 'cancel_sent' });
    expect(requests[0]?.method).toBe('DELETE');
    expect(new URL(requests[0]?.url ?? '').pathname).toBe('/api/paper-trading/orders/1001');
  });

  it('shows the reason when the backend refuses the cancel', async () => {
    const cancelled = await cancelPaperOrder(makeFetch(409, { detail: 'This order belongs to forward test 42.' }), 7);

    expect(cancelled).toEqual({ kind: 'failed', message: 'This order belongs to forward test 42.' });
  });

  it('names the HTTP status when a proxy answers without a message', async () => {
    const proxyFetch: typeof fetch = () => Promise.resolve(new Response('Bad Gateway', { status: 502 }));

    const cancelled = await cancelPaperOrder(proxyFetch, 7);

    expect(cancelled).toEqual({ kind: 'failed', message: 'The cancel request failed with HTTP status 502.' });
  });
});

describe('sendPaperOrder refused by a forward test', () => {
  it('shows which forward test blocks the instrument', async () => {
    const result = readOrderForm(limitForm);
    if (result.kind !== 'valid') {
      throw new Error('The form must be valid.');
    }
    const detail = 'Forward test 3 (Trend v1) trades AAPL / NASDAQ. ATrade refuses orders by hand for this instrument until the forward test stops.';

    const sent = await sendPaperOrder(makeFetch(409, { detail, forward_test_id: 3 }), result.request);

    expect(sent).toEqual({ kind: 'failed', message: `ATrade did not send the order. ${detail}` });
  });
});

describe('readFilledManualOrders', () => {
  const filledOrder: ManualOrder = {
    id: 1,
    created_at_utc: '2026-01-02T03:04:05Z',
    account: 'DU1234567',
    symbol: '700',
    exchange: 'SEHK',
    currency: 'HKD',
    side: 'SELL',
    quantity: 100,
    order_type: 'MKT',
    limit_price: null,
    time_in_force: 'DAY',
    ibkr_order_id: 1001,
    filled_quantity: '100',
    average_fill_price: '380.40',
  };

  it('keeps only the orders by hand with a fill, newest first', async () => {
    const openOrder = { ...filledOrder, id: 2, ibkr_order_id: 1002, filled_quantity: '0', average_fill_price: null };
    const unknownOrder = { ...filledOrder, id: 3, filled_quantity: null, average_fill_price: null };
    const newerFilledOrder = { ...filledOrder, id: 4, ibkr_order_id: 1004 };
    const requests: Request[] = [];

    const orders = await readFilledManualOrders(
      makeFetch(200, { manual_orders: [filledOrder, openOrder, unknownOrder, newerFilledOrder] }, requests),
    );

    expect(orders).toEqual([newerFilledOrder, filledOrder]);
    expect(new URL(requests[0]?.url ?? '').pathname).toBe('/api/paper-trading/manual-orders');
  });

  it('returns null when the backend is not reachable', async () => {
    const orders = await readFilledManualOrders(() => Promise.reject(new TypeError('offline')));

    expect(orders).toBeNull();
  });
});
