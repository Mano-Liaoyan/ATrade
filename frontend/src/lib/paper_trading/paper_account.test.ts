// Turns /ws/paper-trading messages into the text of the account panel.
import { describe, expect, it } from 'vitest';
import { describePaperAccountCheck, formatAmount, readPaperAccountMessage, type PaperAccountMessage } from './paper_account';

const passedMessage: PaperAccountMessage = {
  type: 'account',
  check: { status: 'passed', message: null, actual_accounts: ['DU1234567'], expected_account: 'DU1234567' },
  balance: { net_liquidation_usd: '101234.5', cash_usd: '25000.00' },
  positions: [],
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
