// The order panel of the instrument page (#103): the order is for the instrument of the page, so the panel has no
// instrument fields. These helpers give why the panel cannot send an order, the position of the instrument, the order
// value, and the limit price that the panel starts with.
import { describePaperAccountCheck, type PaperAccountMessage, type PaperPosition } from './paper_account';
import { findOrderBlock, type BlockingForwardTest, type OrderForm } from './paper_orders';

export interface OrderInstrument {
  symbol: string;
  exchange: string;
  currency: string;
}

const START_LIMIT_PRICE_DECIMALS = 2;

/**
 * Why the order panel cannot send an order, or null. The paper account check must pass, and no forward test can trade
 * the instrument (docs/architecture.md section 12.2). The backend checks both again.
 */
export function findInstrumentOrderBlock(
  account: PaperAccountMessage | null,
  instrument: OrderInstrument,
  blockingForwardTests: readonly BlockingForwardTest[],
): string | null {
  if (account === null) {
    return 'Reading the paper account.';
  }
  if (account.check.status !== 'passed' || account.check.actual_accounts[0] === undefined) {
    return describePaperAccountCheck(account.check).title;
  }
  return findOrderBlock({ ...instrument, ...EMPTY_ORDER_FIELDS }, blockingForwardTests);
}

const EMPTY_ORDER_FIELDS: Omit<OrderForm, keyof OrderInstrument> = {
  side: 'BUY',
  quantity: '',
  orderType: 'LMT',
  limitPrice: '',
  timeInForce: 'DAY',
};

/** The position of the instrument in the paper account, or null. */
export function findInstrumentPosition(account: PaperAccountMessage | null, instrument: OrderInstrument): PaperPosition | null {
  return (
    account?.positions.find(
      (position) => position.symbol === instrument.symbol && position.exchange === instrument.exchange,
    ) ?? null
  );
}

/** Quantity times the limit price, or times the last price for a market order. Null when a number is missing. */
export function computeOrderValue(
  form: Pick<OrderForm, 'quantity' | 'orderType' | 'limitPrice'>,
  lastPrice: number | null,
): number | null {
  const quantityText = form.quantity.trim();
  const priceText = form.orderType === 'LMT' ? form.limitPrice.trim() : null;
  if (quantityText === '' || priceText === '') {
    return null;
  }
  const quantity = Number(quantityText);
  const price = priceText === null ? lastPrice : Number(priceText);
  if (price === null || !Number.isFinite(quantity) || !Number.isFinite(price)) {
    return null;
  }
  return quantity * price;
}

/** The limit price that the panel starts with: the last price, for example "187.46". Empty without a last price. */
export function formatStartLimitPrice(lastPrice: number | null): string {
  return lastPrice === null ? '' : lastPrice.toFixed(START_LIMIT_PRICE_DECIMALS);
}
