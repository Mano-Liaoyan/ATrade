// Calls the source order routes (docs/architecture/market_data.md section 8.7.3) and moves a bar source in the order.
import type { components } from '#lib/api';
import { requestJson, type RequestResult } from '#lib/foundation/http_request';

export type BarSource = components['schemas']['BarSource'];
type SourceOrderBody = components['schemas']['SourceOrderBody'];

export type MoveDirection = 'up' | 'down';

const SOURCE_ORDER_PATH = '/api/market-data/source-order';
const FAILED_ACTION = 'The source order request';

const BAR_SOURCE_NAMES: Record<BarSource, string> = { ibkr: 'IBKR', databento: 'Databento' };

export async function readSourceOrder(fetchFunction: typeof fetch): Promise<RequestResult<BarSource[]>> {
  const result = await requestJson<SourceOrderBody>(fetchFunction, FAILED_ACTION, SOURCE_ORDER_PATH);
  return result.kind === 'ok' ? { kind: 'ok', value: result.value.source_order } : result;
}

/** A refused order gives the `detail` text of the backend. */
export async function saveSourceOrder(
  fetchFunction: typeof fetch,
  sourceOrder: BarSource[],
): Promise<RequestResult<BarSource[]>> {
  const result = await requestJson<SourceOrderBody>(fetchFunction, FAILED_ACTION, SOURCE_ORDER_PATH, {
    method: 'PUT',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ source_order: sourceOrder }),
  });
  return result.kind === 'ok' ? { kind: 'ok', value: result.value.source_order } : result;
}

/** The order with the bar source at `index` moved by one place. */
export function moveBarSource(sourceOrder: BarSource[], index: number, direction: MoveDirection): BarSource[] {
  const otherIndex = direction === 'up' ? index - 1 : index + 1;
  const moved = [...sourceOrder];
  const barSource = moved[index];
  const otherBarSource = moved[otherIndex];
  if (barSource === undefined || otherBarSource === undefined) {
    return moved;
  }
  moved[index] = otherBarSource;
  moved[otherIndex] = barSource;
  return moved;
}

export function formatBarSource(barSource: BarSource): string {
  return BAR_SOURCE_NAMES[barSource];
}
