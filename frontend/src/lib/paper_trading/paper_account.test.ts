// Turns /ws/paper-trading messages into the text of the account overview and the Paper tag.
import { describe, expect, it } from 'vite-plus/test';
import {
  describeBalanceCurrency,
  describePaperAccountCheck,
  describePaperAccountTag,
  findPaperAccountCheckKind,
  formatAmount,
  listBalanceMetrics,
  listPositionRows,
  readPaperAccountMessage,
  type PaperAccountBalance,
  type PaperAccountMessage,
  type PaperPosition,
} from './paper_account';

const passedMessage: PaperAccountMessage = {
  type: 'account',
  check: { status: 'passed', message: null, actual_accounts: ['DU1234567'], expected_account: 'DU1234567' },
  balance: {
    net_liquidation_usd: '101234.5',
    cash_usd: '25000.00',
    base_currency: 'USD',
    net_liquidation_base: '101234.5',
    cash_base: '25000.00',
    usd_per_base_unit: '1',
    exchange_rate_source: 'base_currency_is_usd',
    message: null,
  },
  positions: [],
  unattributed_cash_usd: null,
};

describe('readPaperAccountMessage', () => {
  it('reads an account message', () => {
    expect(readPaperAccountMessage(passedMessage)).toEqual(passedMessage);
  });

  it('ignores other messages', () => {
    expect(readPaperAccountMessage({ type: 'heartbeat' })).toBeNull();
    expect(readPaperAccountMessage('account')).toBeNull();
  });
});

describe('findPaperAccountCheckKind', () => {
  it('shows a passed check as success, a check without IB Gateway as warning, and a failed check as error', () => {
    expect(findPaperAccountCheckKind('passed')).toBe('success');
    expect(findPaperAccountCheckKind('disconnected')).toBe('warning');
    expect(findPaperAccountCheckKind('failed')).toBe('error');
  });
});

describe('describePaperAccountCheck', () => {
  it('names the checked paper account', () => {
    expect(describePaperAccountCheck(passedMessage.check)).toEqual({
      title: 'Paper account DU1234567 checked.',
      detail: null,
    });
  });

  it('shows the actual and the expected account when the check fails', () => {
    const description = describePaperAccountCheck({
      status: 'failed',
      message: 'The account DU7654321 from IB Gateway is not the expected account DU1234567.',
      actual_accounts: ['DU7654321'],
      expected_account: 'DU1234567',
    });

    expect(description).toEqual({
      title: 'Paper account check failed. ATrade sends no orders.',
      detail:
        'The account DU7654321 from IB Gateway is not the expected account DU1234567. Actual account: DU7654321. Expected account: DU1234567.',
    });
  });

  it('says when no account is returned or expected', () => {
    const description = describePaperAccountCheck({
      status: 'failed',
      message: 'ATRADE_IBKR_ACCOUNT_ID is not set, so ATrade cannot compare the account.',
      actual_accounts: [],
      expected_account: null,
    });

    expect(description.detail).toContain('Actual account: none. Expected account: not set.');
  });

  it('says that the account is not checked while IB Gateway is not connected', () => {
    const description = describePaperAccountCheck({
      status: 'disconnected',
      message: null,
      actual_accounts: [],
      expected_account: 'DU1234567',
    });

    expect(description).toEqual({ title: 'Paper account not checked. IB Gateway is not connected.', detail: null });
  });
});

describe('formatAmount', () => {
  it('shows 2 decimals with group separators', () => {
    expect(formatAmount('101234.5')).toBe('101,234.50');
    expect(formatAmount('-12')).toBe('-12.00');
  });

  it('shows a dash for a missing amount', () => {
    expect(formatAmount(null)).toBe('–');
  });
});

const eurBalance: PaperAccountBalance = {
  net_liquidation_usd: '111390.00',
  cash_usd: '89112.00',
  base_currency: 'EUR',
  net_liquidation_base: '100000.00',
  cash_base: '80000.00',
  usd_per_base_unit: '1.1139',
  exchange_rate_source: 'ibkr_forex',
  message: null,
};

describe('describeBalanceCurrency', () => {
  it('names the base currency of a USD account', () => {
    expect(describeBalanceCurrency({ ...eurBalance, base_currency: 'USD', usd_per_base_unit: '1', exchange_rate_source: 'base_currency_is_usd' })).toBe('Base currency USD.');
  });

  it('shows the IBKR forex rate that converted a EUR balance', () => {
    expect(describeBalanceCurrency(eurBalance)).toBe(
      'Base currency EUR. Converted to USD with the IBKR EUR.USD rate: 1 EUR = 1.1139 USD.',
    );
  });

  it('shows the account exchange rate that converted a EUR balance', () => {
    expect(describeBalanceCurrency({ ...eurBalance, usd_per_base_unit: '1.25', exchange_rate_source: 'account' })).toBe(
      'Base currency EUR. Converted to USD with the exchange rate of the IBKR account: 1 EUR = 1.25 USD.',
    );
  });

  it('shows why the USD values are missing', () => {
    const message = 'The paper account has the base currency EUR and IBKR sent no EUR to USD exchange rate: timeout';
    expect(
      describeBalanceCurrency({
        ...eurBalance,
        net_liquidation_usd: null,
        cash_usd: null,
        usd_per_base_unit: null,
        exchange_rate_source: null,
        message,
      }),
    ).toBe(message);
  });
});

describe('describePaperAccountTag', () => {
  const passedCheck = passedMessage.check;

  it('names the checked paper account with the middle of the number hidden', () => {
    expect(describePaperAccountTag(passedCheck)).toBe('Paper account DU****567');
  });

  it('hides the middle of each account number', () => {
    expect(describePaperAccountTag({ ...passedCheck, actual_accounts: ['DU1234567', 'U7654321'] })).toBe(
      'Paper account DU****567, U7***321',
    );
  });

  it('hides a short account number completely', () => {
    expect(describePaperAccountTag({ ...passedCheck, actual_accounts: ['DU12'] })).toBe('Paper account ****');
  });

  it('says that the check has not arrived', () => {
    expect(describePaperAccountTag(null)).toBe('Checking the paper account.');
  });

  it('shows no account number when the check did not pass', () => {
    expect(
      describePaperAccountTag({ status: 'failed', message: 'IBKR sent a live account.', actual_accounts: ['U7654321'], expected_account: null }),
    ).toBe('Paper account check failed. ATrade sends no orders.');
    expect(describePaperAccountTag({ status: 'disconnected', message: null, actual_accounts: [], expected_account: null })).toBe(
      'Paper account not checked. IB Gateway is not connected.',
    );
  });
});

describe('listBalanceMetrics', () => {
  it('lists the USD values of a USD account', () => {
    expect(listBalanceMetrics({ ...eurBalance, base_currency: 'USD', net_liquidation_usd: '101234.5', cash_usd: '25000.00' })).toEqual([
      { label: 'Net liquidation (USD)', value: '101,234.50' },
      { label: 'Cash (USD)', value: '25,000.00' },
    ]);
  });

  it('adds the base currency value and the rate of a EUR account', () => {
    expect(listBalanceMetrics(eurBalance)).toEqual([
      { label: 'Net liquidation (USD)', value: '111,390.00' },
      { label: 'Cash (USD)', value: '89,112.00' },
      { label: 'Net liquidation (EUR)', value: '100,000.00' },
      { label: 'USD per EUR', value: '1.1139' },
    ]);
  });

  it('shows a missing value when IBKR sent no rate', () => {
    expect(
      listBalanceMetrics({ ...eurBalance, net_liquidation_usd: null, cash_usd: null, usd_per_base_unit: null }),
    ).toEqual([
      { label: 'Net liquidation (USD)', value: '–' },
      { label: 'Cash (USD)', value: '–' },
      { label: 'Net liquidation (EUR)', value: '100,000.00' },
      { label: 'USD per EUR', value: '–' },
    ]);
  });
});

describe('listPositionRows', () => {
  const position: PaperPosition = {
    symbol: 'AAPL',
    security_type: 'STK',
    exchange: 'NASDAQ',
    currency: 'USD',
    quantity: '80',
    average_cost: '100',
    market_price: '110',
    market_value: '8800',
    unrealized_pnl: '800',
    owners: [
      { owner: { kind: 'by_hand', forward_test_id: null }, quantity: '20', average_cost: '100' },
      { owner: { kind: 'forward_test', forward_test_id: 3 }, quantity: '10', average_cost: '105' },
    ],
    unattributed_quantity: '50',
    split_check: null,
  };

  it('gives one row for each owner and one Unattributed row for the difference', () => {
    expect(
      listPositionRows([position]).map(({ owner, unattributed, quantity, averageCost, marketValue, unrealizedPnl }) => ({
        owner,
        unattributed,
        quantity,
        averageCost,
        marketValue,
        unrealizedPnl,
      })),
    ).toEqual([
      { owner: 'By hand', unattributed: null, quantity: '20', averageCost: '100', marketValue: 2200, unrealizedPnl: 200 },
      { owner: 'Forward test 3', unattributed: null, quantity: '10', averageCost: '105', marketValue: 1100, unrealizedPnl: 50 },
      { owner: null, unattributed: 'Unattributed: 50', quantity: null, averageCost: null, marketValue: null, unrealizedPnl: null },
    ]);
  });

  it('gives one Split check needed row for a position in that state', () => {
    const splitCheck = {
      id: 7,
      stock_split_id: 3,
      split_ratio: '4',
      account_quantity_before: '10',
      account_quantity_after: '40',
    };
    const rows = listPositionRows([{ ...position, unattributed_quantity: '0', split_check: splitCheck }]);
    expect(rows.map((row) => [row.owner, row.splitCheck])).toEqual([
      ['By hand', null],
      ['Forward test 3', null],
      [null, splitCheck],
    ]);
  });

  it('keeps one row with the IBKR values for a position without owners and without a difference', () => {
    const rows = listPositionRows([{ ...position, owners: [], unattributed_quantity: '0' }]);
    expect(rows.map((row) => [row.owner, row.unattributed, row.quantity])).toEqual([[null, null, '80']]);
  });
});
