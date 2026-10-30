// Bar sources and the source order (docs/architecture/market_data.md section 8.7): the read of the global source
// order and the source order choices of the backtest form.
import type { components } from '#lib/api';
import { requestJson, type RequestResult } from '#lib/foundation/http_request';

export type BarSource = components['schemas']['BarSource'];

const SOURCE_ORDER_PATH = '/api/market-data/source-order';

const BAR_SOURCE_NAMES: Record<BarSource, string> = { ibkr: 'IBKR', databento: 'Databento' };

export function formatBarSource(barSource: BarSource): string {
  return BAR_SOURCE_NAMES[barSource];
}

export function formatSourceOrder(sourceOrder: BarSource[]): string {
  return sourceOrder.map(formatBarSource).join(', ');
}

/** Each order of the bar sources once. The given order is first, so it can be the default choice. */
export function listSourceOrders(sourceOrder: BarSource[]): BarSource[][] {
  if (sourceOrder.length <= 1) {
    return [sourceOrder];
  }
  return sourceOrder.flatMap((first, index) =>
    listSourceOrders(sourceOrder.filter((_, otherIndex) => otherIndex !== index)).map((rest) => [first, ...rest]),
  );
}

export async function readSourceOrder(fetchFunction: typeof fetch): Promise<RequestResult<BarSource[]>> {
  const result = await requestJson<components['schemas']['SourceOrderBody']>(
    fetchFunction,
    'Reading the source order',
    SOURCE_ORDER_PATH,
  );
  return result.kind === 'ok' ? { kind: 'ok', value: result.value.source_order } : result;
}
