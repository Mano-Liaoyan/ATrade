// The order panel of the instrument page (#103): the order is for the instrument of the page, so the panel has no
// instrument fields. These helpers give why the panel cannot send an order, the position of the instrument, the order
// value, and the limit price that the panel starts with.
import { describePaperAccountCheck, type PaperAccountMessage, type PaperPosition } from './paper_account';
import type { OrderForm } from './paper_orders';

export interface OrderInstrument {
  symbol: string;
  exchange: string;
  currency: string;
}

const START_LIMIT_PRICE_DECIMALS = 2;

/** A StatusIndicator kind: the paper account is not read yet, a warning, or an error. */
export type InstrumentOrderBlockKind = 'in-progress' | 'warning' | 'error';

export interface InstrumentOrderBlock {
  kind: InstrumentOrderBlockKind;
  text: string;
}

// The status kinds of a paper account check that did not pass, as in findPaperAccountCheckKind.
const FAILED_CHECK_KINDS: Record<'disconnected' | 'failed', InstrumentOrderBlockKind> = {
  disconnected: 'warning',
  failed: 'error',
};

/**
 * Why the order panel cannot send an order, as a status, or null. The paper account check must pass. The backend
 * checks it again. Forward tests and orders by hand share the instruments (docs/architecture/forward_test.md 12.2).
 */
export function findInstrumentOrderBlock(account: PaperAccountMessage | null): InstrumentOrderBlock | null {
  if (account === null) {
    return { kind: 'in-progress', text: 'Reading the paper account.' };
  }
  const { check } = account;
  if (check.status !== 'passed') {
    return { kind: FAILED_CHECK_KINDS[check.status], text: describePaperAccountCheck(check).title };
  }
  if (check.actual_accounts[0] === undefined) {
    return { kind: 'error', text: describePaperAccountCheck(check).title };
  }
  return null;
}

/** The position of the instrument (symbol, exchange, and currency) in the paper account, or null. */
export function findInstrumentPosition(account: PaperAccountMessage | null, instrument: OrderInstrument): PaperPosition | null {
  return (
    account?.positions.find(
      (position) =>
        position.symbol === instrument.symbol &&
        position.exchange === instrument.exchange &&
        position.currency === instrument.currency,
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
