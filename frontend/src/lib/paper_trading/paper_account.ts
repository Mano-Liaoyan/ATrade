// Reads the /ws/paper-trading account messages and describes the paper account check for the account panel.

import type { components } from '#lib/api';
import { readSocketMessage } from '#lib/foundation/live_socket';

// The message models of backend/src/atrade/paper_trading/account_socket.py. Amounts are decimal text.
export type PaperAccountMessage = components['schemas']['PaperAccountMessage'];
export type PaperAccountCheck = components['schemas']['PaperAccountCheckMessage'];
export type PaperPosition = components['schemas']['PositionMessage'];
export type PaperAccountBalance = components['schemas']['PaperAccountBalanceMessage'];

export const PAPER_TRADING_SOCKET_PATH = '/ws/paper-trading';

const AMOUNT_FORMAT = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const MISSING_AMOUNT = '–';

export function readPaperAccountMessage(message: unknown): PaperAccountMessage | null {
  return readSocketMessage<PaperAccountMessage>(message, ['account']);
}

export function describePaperAccountCheck(check: PaperAccountCheck): { title: string; detail: string | null } {
  switch (check.status) {
    case 'passed':
      return { title: `Paper account ${check.actual_accounts.join(', ')} checked.`, detail: null };
    case 'disconnected':
      return { title: 'Paper account not checked. IB Gateway is not connected.', detail: null };
    case 'failed': {
      const actualAccounts = check.actual_accounts.length > 0 ? check.actual_accounts.join(', ') : 'none';
      const expectedAccount = check.expected_account ?? 'not set';
      return {
        title: 'Paper account check failed. ATrade sends no orders.',
        detail: `${check.message ?? ''} Actual account: ${actualAccounts}. Expected account: ${expectedAccount}.`.trim(),
      };
    }
  }
}

// The Paper tag in the header shows the account number with its middle hidden: DU1234567 becomes DU****567.
const SHOWN_LEADING_CHARACTERS = 2;
const SHOWN_TRAILING_CHARACTERS = 3;
const HIDDEN_CHARACTER = '*';

function hideAccountNumberMiddle(account: string): string {
  const hiddenLength = account.length - SHOWN_LEADING_CHARACTERS - SHOWN_TRAILING_CHARACTERS;
  if (hiddenLength < 1) {
    return HIDDEN_CHARACTER.repeat(account.length);
  }
  return (
    account.slice(0, SHOWN_LEADING_CHARACTERS) +
    HIDDEN_CHARACTER.repeat(hiddenLength) +
    account.slice(account.length - SHOWN_TRAILING_CHARACTERS)
  );
}

export function describePaperAccountTag(check: PaperAccountCheck | null): string {
  if (check === null) {
    return 'Checking the paper account.';
  }
  if (check.status !== 'passed') {
    return describePaperAccountCheck(check).title;
  }
  return `Paper account ${check.actual_accounts.map(hideAccountNumberMiddle).join(', ')}`;
}

export function formatAmount(amount: string | null): string {
  if (amount === null) {
    return MISSING_AMOUNT;
  }
  return AMOUNT_FORMAT.format(Number(amount));
}

// ATrade keeps money in USD. The panel names the base currency and the rate that converted the balance (section 11.9).
export function describeBalanceCurrency(balance: PaperAccountBalance): string {
  const baseCurrency = balance.base_currency;
  const rate = balance.usd_per_base_unit;
  if (baseCurrency === null || rate === null) {
    return balance.message ?? 'IBKR sent no balance.';
  }
  switch (balance.exchange_rate_source) {
    case 'ibkr_forex':
      return `Base currency ${baseCurrency}. Converted to USD with the IBKR ${baseCurrency}.USD rate: 1 ${baseCurrency} = ${rate} USD.`;
    case 'account':
      return `Base currency ${baseCurrency}. Converted to USD with the exchange rate of the IBKR account: 1 ${baseCurrency} = ${rate} USD.`;
    default:
      return `Base currency ${baseCurrency}.`;
  }
}
