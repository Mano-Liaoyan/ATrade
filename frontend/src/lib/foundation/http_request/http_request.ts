// Sends HTTP requests to the backend and reads the error message of a failed answer.
// A refused request has ErrorResponse {"detail": "<message>"}. A request that does not validate has
// HTTPValidationError {"detail": [<field error>, ...]}. A proxy can answer without JSON.
import type { components } from '#lib/api';

type ErrorResponse = components['schemas']['ErrorResponse'];
type HTTPValidationError = components['schemas']['HTTPValidationError'];

export type RequestResult<T> = { kind: 'ok'; value: T } | { kind: 'failed'; message: string };

export const BACKEND_NOT_REACHABLE = 'The backend is not reachable.';

/** Returns null when the backend is not reachable. */
export async function sendRequest(fetchFunction: typeof fetch, path: string, init?: RequestInit): Promise<Response | null> {
  try {
    return await fetchFunction(path, init);
  } catch {
    return null;
  }
}

/** Returns null when the body is not JSON. */
export async function readJsonBody(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function hasDetail(body: unknown): body is ErrorResponse | HTTPValidationError {
  return typeof body === 'object' && body !== null && 'detail' in body;
}

/** The message of an error body that was already read. failedAction names the request, like "Reading the bars". */
export function describeErrorBody(body: unknown, status: number, failedAction: string): string {
  const statusMessage = `${failedAction} failed with HTTP status ${String(status)}.`;
  if (!hasDetail(body)) {
    return statusMessage;
  }
  if (typeof body.detail === 'string') {
    return body.detail;
  }
  const firstError = Array.isArray(body.detail) ? body.detail[0] : undefined;
  if (firstError === undefined) {
    return statusMessage;
  }
  return `${String(firstError.loc.at(-1))}: ${firstError.msg}`;
}

export async function readErrorMessage(response: Response, failedAction: string): Promise<string> {
  return describeErrorBody(await readJsonBody(response), response.status, failedAction);
}

/** Sends the request and returns the JSON body, or a message when the backend is not reachable or refuses. */
export async function requestJson<T>(
  fetchFunction: typeof fetch,
  failedAction: string,
  path: string,
  init?: RequestInit,
): Promise<RequestResult<T>> {
  const response = await sendRequest(fetchFunction, path, init);
  if (response === null) {
    return { kind: 'failed', message: BACKEND_NOT_REACHABLE };
  }
  if (!response.ok) {
    return { kind: 'failed', message: await readErrorMessage(response, failedAction) };
  }
  return { kind: 'ok', value: (await response.json()) as T };
}
