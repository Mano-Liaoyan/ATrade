// Calls the strategy HTTP routes (backend/src/atrade/strategy/http_routes.py).

import type { components } from '#lib/api';
import {
  BACKEND_NOT_REACHABLE,
  readErrorMessage,
  requestJson as requestBackendJson,
  sendRequest,
  type RequestResult,
} from '#lib/foundation/http_request';
import type { StrategyRules } from './strategy_rules';

export type StrategyVersionSummary = components['schemas']['StrategyVersionSummary'];
export type StrategyDetail = components['schemas']['StrategyResponse'];
export type StrategyListItem = components['schemas']['StrategyListItem'];
export type StrategyVersion = components['schemas']['StrategyVersionResponse'];
export type CodeProblem = components['schemas']['CodeProblemResponse'];
type CodeCheckFailedResponse = components['schemas']['CodeCheckFailedResponse'];
type RulesCodeResponse = components['schemas']['RulesCodeResponse'];
interface ValidationFailure {
  detail: { loc: (string | number)[]; msg: string }[];
}

export type { RequestResult } from '#lib/foundation/http_request';

export type SaveResult =
  | { kind: 'saved'; version: StrategyVersion; isNewVersion: boolean }
  | { kind: 'check_failed'; problems: CodeProblem[] }
  | { kind: 'failed'; message: string };

export type DeleteResult = { kind: 'deleted' } | { kind: 'failed'; message: string };

const STRATEGIES_PATH = '/api/strategies';
const RULES_CODE_PATH = '/api/strategy-rules/code';
const HTTP_CREATED = 201;
const HTTP_UNPROCESSABLE_CONTENT = 422;
// The strategy routes answer 404 and 409 with ErrorResponse {"detail": "<message>"}.
const FAILED_ACTION = 'The strategy request';

function requestJson<T>(fetchFunction: typeof fetch, path: string, init?: RequestInit): Promise<RequestResult<T>> {
  return requestBackendJson<T>(fetchFunction, FAILED_ACTION, path, init);
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

export function saveStrategyVersion(fetchFunction: typeof fetch, strategyId: number, code: string): Promise<SaveResult> {
  return sendVersion(fetchFunction, strategyId, { code });
}

/** Saves rules of the rule builder. The backend makes the code and saves a version with the source `rule_builder`. */
export function saveStrategyRules(fetchFunction: typeof fetch, strategyId: number, rules: StrategyRules): Promise<SaveResult> {
  return sendVersion(fetchFunction, strategyId, { rules });
}

// A 422 of a rules body that does not match the rules format has the FastAPI validation body {"detail": [...]}.
function readProblems(failure: CodeCheckFailedResponse | ValidationFailure): CodeProblem[] {
  if ('problems' in failure) {
    return failure.problems;
  }
  return failure.detail.map((item) => ({ line: 0, message: `${item.loc.join('.')}: ${item.msg}` }));
}

async function sendVersion(
  fetchFunction: typeof fetch,
  strategyId: number,
  body: { code: string } | { rules: StrategyRules },
): Promise<SaveResult> {
  const path = `${STRATEGIES_PATH}/${String(strategyId)}/versions`;
  const response = await sendRequest(fetchFunction, path, createJsonRequest('POST', body));
  if (response === null) {
    return { kind: 'failed', message: BACKEND_NOT_REACHABLE };
  }
  if (response.status === HTTP_UNPROCESSABLE_CONTENT) {
    const failure = (await response.json()) as CodeCheckFailedResponse | ValidationFailure;
    return { kind: 'check_failed', problems: readProblems(failure) };
  }
  if (!response.ok) {
    return { kind: 'failed', message: await readErrorMessage(response, FAILED_ACTION) };
  }
  const version = (await response.json()) as StrategyVersion;
  return { kind: 'saved', version, isNewVersion: response.status === HTTP_CREATED };
}

/** Makes the code from the rules (`POST /api/strategy-rules/code`). Nothing is saved. */
export async function generateRulesCode(fetchFunction: typeof fetch, rules: StrategyRules): Promise<RequestResult<string>> {
  const result = await requestJson<RulesCodeResponse>(fetchFunction, RULES_CODE_PATH, createJsonRequest('POST', { rules }));
  return result.kind === 'failed' ? result : { kind: 'ok', value: result.value.code };
}

export async function deleteStrategy(fetchFunction: typeof fetch, strategyId: number): Promise<DeleteResult> {
  const response = await sendRequest(fetchFunction, `${STRATEGIES_PATH}/${String(strategyId)}`, { method: 'DELETE' });
  if (response === null) {
    return { kind: 'failed', message: BACKEND_NOT_REACHABLE };
  }
  if (!response.ok) {
    return { kind: 'failed', message: await readErrorMessage(response, FAILED_ACTION) };
  }
  return { kind: 'deleted' };
}
