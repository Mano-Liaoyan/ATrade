// Calls the parameter sweep HTTP routes (backend sweep routes, backtest.md section 10.11.3).

import type { components } from '#lib/api';
import { requestJson as requestBackendJson, type RequestResult } from '#lib/foundation/http_request';

// The generated type makes the fields with a default required. Without them, the route uses its defaults.
export type SweepRequest = Omit<components['schemas']['StartSweepRequest'], 'out_of_sample_share' | 'universe_kind'> &
  Partial<Pick<components['schemas']['StartSweepRequest'], 'out_of_sample_share' | 'universe_kind'>>;
export type Sweep = components['schemas']['SweepResponse'];
export type SweepDetail = components['schemas']['SweepDetailResponse'];
export type SweepRun = components['schemas']['SweepRunResponse'];
export type SweepParameters = components['schemas']['ParametersResponse'];

const SWEEPS_PATH = '/api/sweeps';
const FAILED_ACTION = 'The parameter sweep request';

function requestJson<T>(fetchFunction: typeof fetch, path: string, init?: RequestInit): Promise<RequestResult<T>> {
  return requestBackendJson<T>(fetchFunction, FAILED_ACTION, path, init);
}

export function startSweep(fetchFunction: typeof fetch, request: SweepRequest): Promise<RequestResult<SweepDetail>> {
  return requestJson(fetchFunction, SWEEPS_PATH, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(request),
  });
}

export function listSweeps(fetchFunction: typeof fetch): Promise<RequestResult<Sweep[]>> {
  return requestJson(fetchFunction, SWEEPS_PATH);
}

export function readSweep(fetchFunction: typeof fetch, sweepId: number): Promise<RequestResult<SweepDetail>> {
  return requestJson(fetchFunction, `${SWEEPS_PATH}/${String(sweepId)}`);
}

export function readSweepParameters(
  fetchFunction: typeof fetch,
  strategyVersionId: number,
): Promise<RequestResult<SweepParameters>> {
  return requestJson(fetchFunction, `${SWEEPS_PATH}/parameters?strategy_version_id=${String(strategyVersionId)}`);
}
