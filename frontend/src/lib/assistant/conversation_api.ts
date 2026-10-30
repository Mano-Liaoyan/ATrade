// Calls the conversation routes of port 8000 (docs/architecture/assistant.md 25.11) and the discard route of a
// strategy version (strategy section 9.6).
import type { components } from '#lib/api';
import {
  BACKEND_NOT_REACHABLE,
  readErrorMessage,
  requestJson,
  sendRequest,
  type RequestResult,
} from '#lib/foundation/http_request';

export type Conversation = components['schemas']['ConversationResponse'];
export type ConversationDetail = components['schemas']['ConversationDetailResponse'];

const CONVERSATIONS_PATH = '/api/assistant/conversations';
const FAILED_ACTION = 'The conversation request';

function createJsonRequest(method: string, body: unknown): RequestInit {
  return { method, headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) };
}

export async function listConversations(fetchFunction: typeof fetch, strategyId: number): Promise<RequestResult<Conversation[]>> {
  const path = `${CONVERSATIONS_PATH}?strategy_id=${String(strategyId)}`;
  const result = await requestJson<{ conversations: Conversation[] }>(fetchFunction, FAILED_ACTION, path);
  return result.kind === 'ok' ? { kind: 'ok', value: result.value.conversations } : result;
}

/** The conversation records the open version number in the fixed part of its system prompt (25.9). */
export function createConversation(
  fetchFunction: typeof fetch,
  strategyId: number,
  versionNumber: number | null,
): Promise<RequestResult<Conversation>> {
  const body = { strategy_id: strategyId, version_number: versionNumber };
  return requestJson(fetchFunction, FAILED_ACTION, CONVERSATIONS_PATH, createJsonRequest('POST', body));
}

export function readConversation(fetchFunction: typeof fetch, conversationId: number): Promise<RequestResult<ConversationDetail>> {
  return requestJson(fetchFunction, FAILED_ACTION, `${CONVERSATIONS_PATH}/${String(conversationId)}`);
}

export function renameConversation(
  fetchFunction: typeof fetch,
  conversationId: number,
  title: string,
): Promise<RequestResult<Conversation>> {
  const path = `${CONVERSATIONS_PATH}/${String(conversationId)}`;
  return requestJson(fetchFunction, FAILED_ACTION, path, createJsonRequest('PATCH', { title }));
}

async function sendAction(fetchFunction: typeof fetch, path: string, init: RequestInit, failedAction: string): Promise<string | null> {
  const response = await sendRequest(fetchFunction, path, init);
  if (response === null) {
    return BACKEND_NOT_REACHABLE;
  }
  return response.ok ? null : readErrorMessage(response, failedAction);
}

/** Deletes a conversation. Null when it is deleted, else the error message. */
export function deleteConversation(fetchFunction: typeof fetch, conversationId: number): Promise<string | null> {
  return sendAction(fetchFunction, `${CONVERSATIONS_PATH}/${String(conversationId)}`, { method: 'DELETE' }, FAILED_ACTION);
}

/** Adds the discarded mark to a version that the AI assistant saved. Null when it is discarded, else the error message. */
export function discardStrategyVersion(fetchFunction: typeof fetch, strategyId: number, versionNumber: number): Promise<string | null> {
  const path = `/api/strategies/${String(strategyId)}/versions/${String(versionNumber)}/discard`;
  return sendAction(fetchFunction, path, { method: 'POST' }, 'The strategy request');
}
