// Calls the custom indicator routes (docs/architecture/indicator.md section 23.10).
import type { components } from '#lib/api';
import { BACKEND_NOT_REACHABLE, jsonRequest, readErrorMessage, readJsonBody, requestJson, sendCommand, sendRequest, type RequestResult } from '#lib/foundation/http_request';

export type CustomIndicator = components['schemas']['CustomIndicatorResponse'];
export type CustomIndicatorFields = components['schemas']['CustomIndicatorBody'];
export type CustomIndicatorParameter = components['schemas']['FormulaParameterBody'];
type IndicatorProblem = components['schemas']['IndicatorProblemResponse'];

/** One parameter in the dialog. The numbers are the texts of the fields, so a wrong text stays. */
export interface ParameterDraft {
  name: string;
  label: string;
  value_type: string;
  default: string;
  minimum: string;
  maximum: string;
  description: string;
}

const NUMBER_FIELDS = ['default', 'minimum', 'maximum'] as const;

const NEW_PARAMETER: ParameterDraft = { name: '', label: '', value_type: 'int', default: '', minimum: '', maximum: '', description: '' };

export function createParameterDraft(parameter?: CustomIndicatorParameter): ParameterDraft {
  if (parameter === undefined) {
    return { ...NEW_PARAMETER };
  }
  return { ...NEW_PARAMETER, ...parameter, default: String(parameter.default), minimum: String(parameter.minimum), maximum: String(parameter.maximum) };
}

/** The parameters of the request, or the problem of each number field that has no number. */
export function readParameterDrafts(drafts: readonly ParameterDraft[]): { parameters: CustomIndicatorParameter[]; problems: CustomIndicatorProblems } {
  const problems: CustomIndicatorProblems = {};
  const parameters = drafts.map((draft, index) => {
    for (const field of NUMBER_FIELDS) {
      if (draft[field].trim() === '' || !Number.isFinite(Number(draft[field]))) {
        problems[`parameters.${String(index)}.${field}`] = 'Enter a number.';
      }
    }
    return { ...draft, default: Number(draft.default), minimum: Number(draft.minimum), maximum: Number(draft.maximum) };
  });
  return { parameters, problems };
}

/** The message of each field with a problem, by the location with `.` between its parts, for example `name` or
 * `parameters.0.default`. A problem without a field has the key "". */
export type CustomIndicatorProblems = Record<string, string>;
export type SaveResult = { kind: 'ok' } | { kind: 'refused'; problems: CustomIndicatorProblems } | { kind: 'failed'; message: string };

export const CUSTOM_INDICATORS_SOCKET_PATH = '/ws/custom-indicators';
const BASE_PATH = '/api/custom-indicators';
const FAILED_ACTION = 'The custom indicator request';

export function listCustomIndicators(fetchFunction: typeof fetch): Promise<RequestResult<CustomIndicator[]>> {
  return requestJson<CustomIndicator[]>(fetchFunction, FAILED_ACTION, BASE_PATH);
}

/** The first problem of each field. */
export function groupProblems(problems: readonly IndicatorProblem[]): CustomIndicatorProblems {
  const grouped: CustomIndicatorProblems = {};
  for (const problem of problems) {
    grouped[problem.location.join('.')] ??= problem.message;
  }
  return grouped;
}

/** Creates a custom indicator, or changes the one with `customIndicatorId`. */
export async function saveCustomIndicator(fetchFunction: typeof fetch, customIndicatorId: number | null, fields: CustomIndicatorFields): Promise<SaveResult> {
  const response = await sendRequest(fetchFunction, customIndicatorId === null ? BASE_PATH : `${BASE_PATH}/${String(customIndicatorId)}`, jsonRequest(customIndicatorId === null ? 'POST' : 'PUT', fields));
  if (response === null) {
    return { kind: 'failed', message: BACKEND_NOT_REACHABLE };
  }
  if (response.ok) {
    return { kind: 'ok' };
  }
  const problems = ((await readJsonBody(response.clone())) as { problems?: IndicatorProblem[] } | null)?.problems;
  if (Array.isArray(problems)) {
    return { kind: 'refused', problems: groupProblems(problems) };
  }
  return { kind: 'failed', message: await readErrorMessage(response, FAILED_ACTION) };
}

/** Keep: the AI assistant cannot change the custom indicator after it (section 23.10.6). */
export function keepCustomIndicator(fetchFunction: typeof fetch, customIndicatorId: number): Promise<RequestResult<undefined>> {
  return sendCommand(fetchFunction, FAILED_ACTION, `${BASE_PATH}/${String(customIndicatorId)}/keep`, { method: 'POST' });
}

export function deleteCustomIndicator(fetchFunction: typeof fetch, customIndicatorId: number): Promise<RequestResult<undefined>> {
  return sendCommand(fetchFunction, FAILED_ACTION, `${BASE_PATH}/${String(customIndicatorId)}`, { method: 'DELETE' });
}
