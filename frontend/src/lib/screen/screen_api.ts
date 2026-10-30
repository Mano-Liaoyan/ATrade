// Calls the screen HTTP routes (backend/src/atrade/screen/http_routes.py, screen.md section 24.7).
import type { components } from '#lib/api';
import { requestJson, type RequestResult } from '#lib/foundation/http_request';

export type ScreenListItem = components['schemas']['ScreenListItemResponse'];
export type Screen = components['schemas']['ScreenResponse'];
export type ScreenResult = components['schemas']['ScreenResultResponse'];
export type ScreenResultExclusion = components['schemas']['ScreenResultExclusionResponse'];

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
