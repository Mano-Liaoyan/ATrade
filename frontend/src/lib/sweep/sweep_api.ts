// Calls the parameter sweep HTTP routes (backend sweep routes, backtest.md section 10.11.3).

import type { components } from '#lib/api';
import { jsonRequest, requestJson, type RequestResult } from '#lib/foundation/http_request';

// The generated type makes the fields with a default required. Without them, the route uses its defaults.
export type SweepRequest = Omit<components['schemas']['StartSweepRequest'], 'out_of_sample_share' | 'universe_kind'> &
  Partial<Pick<components['schemas']['StartSweepRequest'], 'out_of_sample_share' | 'universe_kind'>>;
export type Sweep = components['schemas']['SweepResponse'];
export type SweepDetail = components['schemas']['SweepDetailResponse'];
export type SweepRun = components['schemas']['SweepRunResponse'];
export type SweepParameters = components['schemas']['ParametersResponse'];

// The change socket of the list: a "changed" message after each change (foundation/live_socket readOnChange).
export const SWEEPS_SOCKET_PATH = '/ws/sweeps';
const SWEEPS_PATH = '/api/sweeps';
const FAILED_ACTION = 'The parameter sweep request';

export function startSweep(fetchFunction: typeof fetch, request: SweepRequest): Promise<RequestResult<SweepDetail>> {
  return requestJson(fetchFunction, FAILED_ACTION, SWEEPS_PATH, jsonRequest('POST', request));
}

export function listSweeps(fetchFunction: typeof fetch): Promise<RequestResult<Sweep[]>> {
  return requestJson(fetchFunction, FAILED_ACTION, SWEEPS_PATH);
}

export function readSweep(fetchFunction: typeof fetch, sweepId: number): Promise<RequestResult<SweepDetail>> {
  return requestJson(fetchFunction, FAILED_ACTION, `${SWEEPS_PATH}/${String(sweepId)}`);
}

export function readSweepParameters(
  fetchFunction: typeof fetch,
  strategyVersionId: number,
): Promise<RequestResult<SweepParameters>> {
  return requestJson(fetchFunction, FAILED_ACTION, `${SWEEPS_PATH}/parameters?strategy_version_id=${String(strategyVersionId)}`);
}
