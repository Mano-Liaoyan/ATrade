// Reads the /ws/paper-trading account messages and describes the paper account check for the account panel.

import type { components } from '#lib/api';
import { readSocketMessage } from '#lib/foundation/live_socket';

// The message models of backend/src/atrade/paper_trading/account_socket.py. Amounts are decimal text.
export type PaperAccountMessage = components['schemas']['PaperAccountMessage'];
export type PaperAccountCheck = components['schemas']['PaperAccountCheckMessage'];
export type PaperPosition = components['schemas']['PositionMessage'];

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

export function formatAmount(amount: string | null): string {
  if (amount === null) {
    return MISSING_AMOUNT;
  }
  return AMOUNT_FORMAT.format(Number(amount));
}
