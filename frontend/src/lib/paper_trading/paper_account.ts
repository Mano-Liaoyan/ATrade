// Reads the /ws/paper-trading account messages and describes the paper account check for the account panel.

// Hand-written until the OpenAPI type generation covers WebSocket messages.
// It matches PaperAccountMessage in backend/src/atrade/paper_trading/http_routes.py. Amounts are decimal text.
export interface PaperAccountCheck {
  status: 'disconnected' | 'passed' | 'failed';
  message: string | null;
  actual_accounts: string[];
  expected_account: string | null;
}

export interface PaperAccountBalance {
  net_liquidation_usd: string | null;
  cash_usd: string | null;
}

export interface PaperPosition {
  symbol: string;
  security_type: string;
  exchange: string;
  currency: string;
  quantity: string;
  average_cost: string;
  market_price: string;
  market_value: string;
  unrealized_pnl: string;
}

export interface PaperAccountMessage {
  type: 'account';
  check: PaperAccountCheck;
  balance: PaperAccountBalance | null;
  positions: PaperPosition[];
}

export const PAPER_TRADING_SOCKET_PATH = '/ws/paper-trading';

const AMOUNT_FORMAT = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const MISSING_AMOUNT = '–';

export function readPaperAccountMessage(message: unknown): PaperAccountMessage | null {
  if (typeof message !== 'object' || message === null || !('type' in message) || message.type !== 'account') {
    return null;
  }
  return message as PaperAccountMessage;
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
