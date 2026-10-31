// The allocated capital of the start dialog (docs/architecture/forward_test.md 12.16, 12.18): reads the unallocated
// amount of the paper account from GET /api/forward-tests/capital and finds the reason that blocks the start.
import type { components } from '#lib/api';
import { formatAmount } from '#lib/foundation/value_format';
import { readJsonBody, sendRequest } from '#lib/foundation/http_request';

export type ForwardTestCapital = components['schemas']['ForwardTestCapitalResponse'];

const CAPITAL_PATH = '/api/forward-tests/capital';

/** Null when the backend is not reachable or refuses the request. */
export async function readForwardTestCapital(fetchFunction: typeof fetch): Promise<ForwardTestCapital | null> {
  const response = await sendRequest(fetchFunction, CAPITAL_PATH);
  if (response?.ok !== true) {
    return null;
  }
  return (await readJsonBody(response)) as ForwardTestCapital;
}

export function describeUnallocated(unallocatedUsd: string): string {
  return `Unallocated: ${formatAmount(unallocatedUsd)} USD`;
}

/**
 * The reason that blocks the start, or null. Without an unallocated amount, `unavailableReason` (for example the
 * reason of the paper account check) blocks the start: the backend refuses it too.
 */
export function findCapitalBlockReason(
  capitalText: string,
  unallocatedUsd: string | null,
  unavailableReason: string,
): string | null {
  if (unallocatedUsd === null) {
    return unavailableReason;
  }
  const capital = capitalText.trim();
  if (capital !== '' && Number(capital) > Number(unallocatedUsd)) {
    return `Capital is larger than the unallocated ${formatAmount(unallocatedUsd)} USD`;
  }
  return null;
}
