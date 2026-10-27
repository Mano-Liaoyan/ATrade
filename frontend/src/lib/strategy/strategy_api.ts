// Calls the strategy HTTP routes (backend/src/atrade/strategy/http_routes.py).

import type { components } from '#lib/api';

export type StrategyVersionSummary = components['schemas']['StrategyVersionSummary'];
export type StrategyDetail = components['schemas']['StrategyResponse'];
export type StrategyListItem = components['schemas']['StrategyListItem'];
export type StrategyVersion = components['schemas']['StrategyVersionResponse'];
export type CodeProblem = components['schemas']['CodeProblemResponse'];
// The strategy routes do not declare their error model. FastAPI HTTPException sends {"detail": "<message>"}.
interface ErrorResponse {
  detail: string;
}
type CodeCheckFailedResponse = components['schemas']['CodeCheckFailedResponse'];

export type RequestResult<T> = { kind: 'ok'; value: T } | { kind: 'failed'; message: string };

export type SaveResult =
  | { kind: 'saved'; version: StrategyVersion; isNewVersion: boolean }
  | { kind: 'check_failed'; problems: CodeProblem[] }
  | { kind: 'failed'; message: string };

export type DeleteResult = { kind: 'deleted' } | { kind: 'failed'; message: string };

const STRATEGIES_PATH = '/api/strategies';
const HTTP_CREATED = 201;
const HTTP_UNPROCESSABLE_CONTENT = 422;
const BACKEND_NOT_REACHABLE = 'The backend is not reachable.';

async function sendRequest(fetchFunction: typeof fetch, path: string, init?: RequestInit): Promise<Response | null> {
  try {
    return await fetchFunction(path, init);
  } catch {
    return null;
  }
}

async function readFailureMessage(response: Response): Promise<string> {
  try {
    const failure = (await response.json()) as ErrorResponse;
    return typeof failure.detail === 'string' ? failure.detail : `Request failed with status ${String(response.status)}.`;
  } catch {
    return `Request failed with status ${String(response.status)}.`;
  }
}

async function requestJson<T>(fetchFunction: typeof fetch, path: string, init?: RequestInit): Promise<RequestResult<T>> {
  const response = await sendRequest(fetchFunction, path, init);
  if (response === null) {
    return { kind: 'failed', message: BACKEND_NOT_REACHABLE };
  }
  if (!response.ok) {
    return { kind: 'failed', message: await readFailureMessage(response) };
  }
  return { kind: 'ok', value: (await response.json()) as T };
}

function createJsonRequest(method: string, body: unknown): RequestInit {
  return { method, headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) };
}

export function listStrategies(fetchFunction: typeof fetch): Promise<RequestResult<StrategyListItem[]>> {
  return requestJson(fetchFunction, STRATEGIES_PATH);
}

export function readStrategy(fetchFunction: typeof fetch, strategyId: number): Promise<RequestResult<StrategyDetail>> {
  return requestJson(fetchFunction, `${STRATEGIES_PATH}/${String(strategyId)}`);
}

export function readStrategyVersion(
  fetchFunction: typeof fetch,
  strategyId: number,
  versionNumber: number,
): Promise<RequestResult<StrategyVersion>> {
  return requestJson(fetchFunction, `${STRATEGIES_PATH}/${String(strategyId)}/versions/${String(versionNumber)}`);
}

export async function createStrategy(
  fetchFunction: typeof fetch,
  name: string,
): Promise<{ kind: 'created'; strategy: StrategyDetail } | { kind: 'failed'; message: string }> {
  const result = await requestJson<StrategyDetail>(fetchFunction, STRATEGIES_PATH, createJsonRequest('POST', { name }));
  if (result.kind === 'failed') {
    return result;
  }
  return { kind: 'created', strategy: result.value };
}

export async function saveStrategyVersion(fetchFunction: typeof fetch, strategyId: number, code: string): Promise<SaveResult> {
  const path = `${STRATEGIES_PATH}/${String(strategyId)}/versions`;
  const response = await sendRequest(fetchFunction, path, createJsonRequest('POST', { code }));
  if (response === null) {
    return { kind: 'failed', message: BACKEND_NOT_REACHABLE };
  }
  if (response.status === HTTP_UNPROCESSABLE_CONTENT) {
    const failure = (await response.json()) as CodeCheckFailedResponse;
    return { kind: 'check_failed', problems: failure.problems };
  }
  if (!response.ok) {
    return { kind: 'failed', message: await readFailureMessage(response) };
  }
  const version = (await response.json()) as StrategyVersion;
  return { kind: 'saved', version, isNewVersion: response.status === HTTP_CREATED };
}

export async function deleteStrategy(fetchFunction: typeof fetch, strategyId: number): Promise<DeleteResult> {
  const response = await sendRequest(fetchFunction, `${STRATEGIES_PATH}/${String(strategyId)}`, { method: 'DELETE' });
  if (response === null) {
    return { kind: 'failed', message: BACKEND_NOT_REACHABLE };
  }
  if (!response.ok) {
    return { kind: 'failed', message: await readFailureMessage(response) };
  }
  return { kind: 'deleted' };
}
