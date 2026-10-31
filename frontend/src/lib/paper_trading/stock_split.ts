// The "Split check needed" state of a position (docs/architecture/paper_trading.md sections 11.7 and 11.11): the ratio,
// the IBKR share counts, and the 2 routes "Apply split" and "Keep ledger".
import type { components } from '#lib/api';
import { readErrorMessage, sendRequest } from '#lib/foundation/http_request';
import { formatSplitRatio } from '#lib/foundation/value_format';

export type SplitCheck = components['schemas']['SplitCheckMessage'];
export type SplitCheckResult = { kind: 'done' } | { kind: 'failed'; message: string };

export interface SplitCheckText {
  /** New shares to old shares, for example "4:1". */
  ratio: string;
  /** The IBKR share count before and after, for example "10 → 40". */
  shareCounts: string;
  applyLabel: string;
}

const STOCK_SPLITS_PATH = '/api/paper-trading/stock-splits';

export function describeSplitCheck(splitCheck: SplitCheck): SplitCheckText {
  const ratio = formatSplitRatio(splitCheck.split_ratio);
  return {
    ratio,
    shareCounts: `${splitCheck.account_quantity_before} → ${splitCheck.account_quantity_after}`,
    applyLabel: `Apply split ${ratio}`,
  };
}

async function postSplitCheckAction(
  fetchFunction: typeof fetch,
  splitCheckId: number,
  action: 'apply' | 'keep-ledger',
  failedAction: string,
): Promise<SplitCheckResult> {
  const response = await sendRequest(fetchFunction, `${STOCK_SPLITS_PATH}/${String(splitCheckId)}/${action}`, {
    method: 'POST',
  });
  if (response === null) {
    return { kind: 'failed', message: 'Backend not reachable. ATrade did not change the split check.' };
  }
  if (!response.ok) {
    return { kind: 'failed', message: await readErrorMessage(response, failedAction) };
  }
  return { kind: 'done' };
}

export function applyStockSplit(fetchFunction: typeof fetch, splitCheckId: number): Promise<SplitCheckResult> {
  return postSplitCheckAction(fetchFunction, splitCheckId, 'apply', 'Apply split');
}

export function keepLedger(fetchFunction: typeof fetch, splitCheckId: number): Promise<SplitCheckResult> {
  return postSplitCheckAction(fetchFunction, splitCheckId, 'keep-ledger', 'Keep ledger');
}
