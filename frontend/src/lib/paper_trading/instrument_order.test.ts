// The order panel of the instrument page: why the panel cannot send an order, the position of the instrument, the
// order value, and the start limit price.
import { describe, expect, it } from 'vite-plus/test';
import { computeOrderValue, findInstrumentOrderBlock, findInstrumentPosition, formatStartLimitPrice } from './instrument_order';
import type { PaperAccountMessage, PaperPosition } from './paper_account';

const AAPL = { symbol: 'AAPL', exchange: 'NASDAQ', currency: 'USD' };

function makePosition(symbol: string, exchange: string, quantity: string): PaperPosition {
  return {
    symbol,
    security_type: 'STK',
    exchange,
    currency: 'USD',
    quantity,
    average_cost: '100.00',
    market_price: '110.00',
    market_value: '1100.00',
    unrealized_pnl: '100.00',
  };
}

function makeAccount(check: PaperAccountMessage['check'], positions: PaperPosition[] = []): PaperAccountMessage {
  return { type: 'account', check, balance: null, positions };
}

const PASSED = { status: 'passed', message: null, actual_accounts: ['DU1234567'], expected_account: 'DU1234567' } as PaperAccountMessage['check'];

describe('findInstrumentOrderBlock', () => {
  it('blocks the order while the paper account is not read', () => {
    expect(findInstrumentOrderBlock(null, AAPL, [])).toEqual({ kind: 'in-progress', text: 'Reading the paper account.' });
  });

  it('blocks the order when IB Gateway is not connected', () => {
    const account = makeAccount({ status: 'disconnected', message: null, actual_accounts: [], expected_account: null });
    expect(findInstrumentOrderBlock(account, AAPL, [])).toEqual({
      kind: 'warning',
      text: 'Paper account not checked. IB Gateway is not connected.',
    });
  });

  it('blocks the order when the paper account check failed', () => {
    const account = makeAccount({ status: 'failed', message: 'Wrong account.', actual_accounts: ['U1'], expected_account: 'DU1' });
    expect(findInstrumentOrderBlock(account, AAPL, [])).toEqual({
      kind: 'error',
      text: 'Paper account check failed. ATrade sends no orders.',
    });
  });

  it('blocks the order when a forward test trades the instrument', () => {
    const blocking = [{ label: 'Forward test 7 (Bar count v1)', symbol: 'AAPL', exchange: 'NASDAQ' }];
    expect(findInstrumentOrderBlock(makeAccount(PASSED), AAPL, blocking)).toEqual({
      kind: 'warning',
      text: 'Forward test 7 (Bar count v1) trades AAPL / NASDAQ. Stop the forward test to send an order by hand.',
    });
  });

  it('lets the order go when the check passed and no forward test trades the instrument', () => {
    const blocking = [{ label: 'Forward test 7 (Bar count v1)', symbol: 'MSFT', exchange: 'NASDAQ' }];
    expect(findInstrumentOrderBlock(makeAccount(PASSED), AAPL, blocking)).toBeNull();
  });
});

describe('findInstrumentPosition', () => {
  it('finds the position of the instrument by symbol and exchange', () => {
    const positions = [makePosition('MSFT', 'NASDAQ', '5'), makePosition('AAPL', 'NASDAQ', '12')];
    expect(findInstrumentPosition(makeAccount(PASSED, positions), AAPL)?.quantity).toBe('12');
  });

  it('gives null without a position or without the account', () => {
    expect(findInstrumentPosition(makeAccount(PASSED, [makePosition('AAPL', 'ARCA', '1')]), AAPL)).toBeNull();
    expect(findInstrumentPosition(makeAccount(PASSED, [makePosition('AAPL', 'NASDAQ', '1')]), { ...AAPL, currency: 'EUR' })).toBeNull();
    expect(findInstrumentPosition(null, AAPL)).toBeNull();
  });
});

describe('computeOrderValue', () => {
  it('multiplies the quantity by the limit price of a limit order', () => {
    expect(computeOrderValue({ quantity: '3', orderType: 'LMT', limitPrice: '1.25' }, 200)).toBe(3.75);
  });

  it('multiplies the quantity by the last price of a market order', () => {
    expect(computeOrderValue({ quantity: '4', orderType: 'MKT', limitPrice: '1.25' }, 2.5)).toBe(10);
  });

  it('gives null when a number is missing or not a number', () => {
    expect(computeOrderValue({ quantity: '', orderType: 'LMT', limitPrice: '1.25' }, 2)).toBeNull();
    expect(computeOrderValue({ quantity: 'x', orderType: 'LMT', limitPrice: '1.25' }, 2)).toBeNull();
    expect(computeOrderValue({ quantity: '2', orderType: 'LMT', limitPrice: '' }, 2)).toBeNull();
    expect(computeOrderValue({ quantity: '2', orderType: 'MKT', limitPrice: '' }, null)).toBeNull();
  });
});

describe('formatStartLimitPrice', () => {
  it('writes the last price with 2 decimals, or nothing without a last price', () => {
    expect(formatStartLimitPrice(187.456)).toBe('187.46');
    expect(formatStartLimitPrice(null)).toBe('');
  });
});
