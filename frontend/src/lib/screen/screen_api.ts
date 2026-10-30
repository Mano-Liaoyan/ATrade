// Calls the screen HTTP routes (backend/src/atrade/screen/http_routes.py, screen.md section 24.7).
import type { components } from '#lib/api';
import { readJsonBody, readErrorMessage, requestJson, sendRequest, BACKEND_NOT_REACHABLE, type RequestResult } from '#lib/foundation/http_request';

export type ScreenListItem = components['schemas']['ScreenListItemResponse'];
export type Screen = components['schemas']['ScreenResponse'];
export type ScreenResult = components['schemas']['ScreenResultResponse'];
export type ScreenResultExclusion = components['schemas']['ScreenResultExclusionResponse'];
export type ScreenIndicator = components['schemas']['ScreenIndicatorResponse'];
export type ScreenProblem = components['schemas']['ScreenProblemResponse'];
/** A save or a run of a screen. `check_failed` has the problems of the 422 answer (section 24.6). */
export type ScreenCheckResult<T> = RequestResult<T> | { kind: 'check_failed'; problems: ScreenProblem[] };

export type { RequestResult } from '#lib/foundation/http_request';

const FAILED_ACTION = 'The screen request';
// The screen page shows all rows of a screen result (at most 500, section 24.4) and sorts them itself.
const ALL_ROWS_LIMIT = 500;

export function listScreens(fetchFunction: typeof fetch): Promise<RequestResult<ScreenListItem[]>> {
  return requestJson(fetchFunction, FAILED_ACTION, '/api/screens');
}

export function readScreen(fetchFunction: typeof fetch, screenId: number): Promise<RequestResult<Screen>> {
  return requestJson(fetchFunction, FAILED_ACTION, `/api/screens/${String(screenId)}`);
}

const JSON_HEADERS = { 'Content-Type': 'application/json' };

const UNPROCESSABLE_CONTENT = 422;

async function requestChecked<T>(
  fetchFunction: typeof fetch,
  path: string,
  init: RequestInit,
): Promise<ScreenCheckResult<T>> {
  const response = await sendRequest(fetchFunction, path, init);
  if (response === null) {
    return { kind: 'failed', message: BACKEND_NOT_REACHABLE };
  }
  if (response.status === UNPROCESSABLE_CONTENT) {
    const body = (await readJsonBody(response.clone())) as { problems?: ScreenProblem[] } | null;
    if (Array.isArray(body?.problems)) {
      return { kind: 'check_failed', problems: body.problems };
    }
  }
  if (!response.ok) {
    return { kind: 'failed', message: await readErrorMessage(response, FAILED_ACTION) };
  }
  return { kind: 'ok', value: (await response.json()) as T };
}

/** Runs the market and the definition of the draft for the screen. The saved screen does not change (section 24.13). */
export function runScreenDraft(
  fetchFunction: typeof fetch,
  screenId: number,
  draft: { market: string; definition: unknown },
): Promise<ScreenCheckResult<ScreenResult>> {
  return requestChecked(fetchFunction, `/api/screens/${String(screenId)}/runs`, {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify(draft),
  });
}

/** The indicator catalog for the edit popover (section 24.7). */
export function listScreenIndicators(fetchFunction: typeof fetch): Promise<RequestResult<ScreenIndicator[]>> {
  return requestJson(fetchFunction, FAILED_ACTION, '/api/screen-indicators');
}

/** "Save screen": overwrites the definition of the saved screen. */
export function saveScreen(
  fetchFunction: typeof fetch,
  screen: { id: number; name: string },
  definition: unknown,
): Promise<ScreenCheckResult<Screen>> {
  return requestChecked(fetchFunction, `/api/screens/${String(screen.id)}`, {
    method: 'PUT',
    headers: JSON_HEADERS,
    body: JSON.stringify({ name: screen.name, definition }),
  });
}

/** "Save as new screen". */
export function createScreen(
  fetchFunction: typeof fetch,
  screen: { name: string; market: string; definition: unknown },
): Promise<ScreenCheckResult<Screen>> {
  return requestChecked(fetchFunction, '/api/screens', {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify(screen),
  });
}

export function readScreenResult(
  fetchFunction: typeof fetch,
  screenResultId: number,
): Promise<RequestResult<ScreenResult>> {
  return requestJson(
    fetchFunction,
    FAILED_ACTION,
    `/api/screen-results/${String(screenResultId)}?limit=${String(ALL_ROWS_LIMIT)}`,
  );
}
