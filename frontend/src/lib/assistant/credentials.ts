// The Credentials dialog (docs/architecture/assistant.md 25.7): the credential list, the provider list, and the steps
// of one login on /ws/assistant. The secrets stay in the assistant service. The page sees only the last 4
// characters of an API key. An API key goes from the password field to /ws/assistant as a login_answer.
import type { components } from '#lib/api';
import type { SelectItem, StatusKind } from '#lib/foundation/carbon';
import { requestJson, sendCommand, type RequestResult } from '#lib/foundation/http_request';
import { readSocketMessage } from '#lib/foundation/live_socket';

export type Credential = components['schemas']['CredentialResponse'];
export type Provider = components['schemas']['ProviderResponse'];
export type LoginMethod = Provider['login_methods'][number];
export type LoginStepMessage = components['schemas']['LoginStepMessage'];
type LoginEndMessage = components['schemas']['LoginEndMessage'];
type AssistantErrorMessage = components['schemas']['AssistantErrorMessage'];
export type LoginMessage = LoginStepMessage | LoginEndMessage | AssistantErrorMessage;

const ASSISTANT_PATH = '/api/assistant';
const FAILED_ACTION = 'The credential request';
const KEY_MASK = '••••';
const LOGIN_MESSAGE_TYPES: LoginMessage['type'][] = ['login_step', 'login_end', 'error'];

export function listCredentials(fetchFunction: typeof fetch): Promise<RequestResult<{ credentials: Credential[] }>> {
  return requestJson(fetchFunction, FAILED_ACTION, `${ASSISTANT_PATH}/credentials`);
}

export function listProviders(fetchFunction: typeof fetch): Promise<RequestResult<{ providers: Provider[] }>> {
  return requestJson(fetchFunction, FAILED_ACTION, `${ASSISTANT_PATH}/providers`);
}

/** Deletes a credential. Null when it is deleted, else the error message. */
export async function deleteCredential(fetchFunction: typeof fetch, credentialId: string): Promise<string | null> {
  const path = `${ASSISTANT_PATH}/credentials/${encodeURIComponent(credentialId)}`;
  const result = await sendCommand(fetchFunction, FAILED_ACTION, path, { method: 'DELETE' });
  return result.kind === 'failed' ? result.message : null;
}

/** The key column: the last 4 characters of an API key. Empty for a subscription login. */
export function formatKey(credential: Credential): string {
  return credential.key_last4 === null ? '' : `${KEY_MASK}${credential.key_last4}`;
}

export function describeCredentialKind(type: Credential['type']): string {
  switch (type) {
    case 'oauth':
      return 'Subscription';
    case 'api_key':
      return 'API key';
    case 'claude_code':
      return 'Claude Code login';
  }
}

/** pi's own Anthropic subscription login: pi sends the Claude subscription token to the Anthropic API itself.
 * Anthropic permits a Claude subscription only in Claude Code and its own apps (docs/architecture/assistant.md 25.7.5). */
export function isAnthropicSubscription(provider: string, method: Credential['type']): boolean {
  return provider === 'anthropic' && method === 'oauth';
}

export const ANTHROPIC_SUBSCRIPTION_RISK_TITLE = 'Anthropic does not permit this login';
export const ANTHROPIC_SUBSCRIPTION_RISK =
  'pi sends the Claude subscription token to the Anthropic API outside Claude Code. Anthropic can limit or close the ' +
  'account. Use the Claude Code login for a Claude subscription.';

/** The status icon before the credential name. `label` is its accessible name and tooltip, with the reason of a failure. */
export interface CredentialStateView {
  kind: StatusKind;
  label: string;
}

/** "failed": the last OAuth refresh failed. The user deletes the credential and logs in again. A Claude Code login
 * that is not ready gives its reason and the login command. A ready Anthropic subscription of pi shows its risk. */
export function describeCredentialState(credential: Credential): CredentialStateView {
  if (credential.type === 'claude_code' && credential.state === 'failed') {
    return { kind: 'error', label: credential.state_message ?? 'Claude Code is not ready.' };
  }
  if (credential.state === 'ready') {
    return isAnthropicSubscription(credential.provider, credential.type)
      ? { kind: 'warning', label: `Ready. ${ANTHROPIC_SUBSCRIPTION_RISK_TITLE}: ${ANTHROPIC_SUBSCRIPTION_RISK}` }
      : { kind: 'success', label: 'Ready' };
  }
  return { kind: 'error', label: `Log in again: ${credential.state_message ?? 'The OAuth refresh failed.'}` };
}

/** The providers that have the login method, for the Provider select. */
export function listLoginProviders(providers: Provider[], method: LoginMethod): SelectItem<string>[] {
  return providers
    .filter((provider) => provider.login_methods.includes(method))
    .map((provider) => ({ value: provider.id, label: provider.name }));
}

export interface LoginView {
  phase: 'idle' | 'running' | 'failed';
  authUrl: string | null;
  authInstructions: string | null;
  deviceCode: { userCode: string; url: string | null } | null;
  progress: string | null;
  /** The prompt step that waits for an answer. */
  prompt: LoginStepMessage | null;
  error: string | null;
}

export const NO_LOGIN: LoginView = {
  phase: 'idle',
  authUrl: null,
  authInstructions: null,
  deviceCode: null,
  progress: null,
  prompt: null,
  error: null,
};

export const STARTED_LOGIN: LoginView = { ...NO_LOGIN, phase: 'running' };

function addLoginStep(login: LoginView, step: LoginStepMessage): LoginView {
  const running: LoginView = { ...login, phase: 'running', error: null };
  switch (step.step) {
    case 'auth_url':
      return { ...running, authUrl: step.url, authInstructions: step.message };
    case 'device_code':
      return { ...running, deviceCode: step.user_code === null ? null : { userCode: step.user_code, url: step.url } };
    case 'progress':
    case 'info':
      return { ...running, progress: step.message };
    case 'prompt':
      return { ...running, prompt: step };
  }
}

/** The login after one message of /ws/assistant. login_end ends the login: the dialog reads the list again. */
export function addLoginMessage(login: LoginView, message: LoginMessage): LoginView {
  switch (message.type) {
    case 'login_step':
      return addLoginStep(login, message);
    case 'login_end':
      return NO_LOGIN;
    case 'error':
      return { ...login, phase: 'failed', prompt: null, error: message.message };
  }
}

/** True while the login runs and shows nothing to do: before the first step of pi (about 9 s) and after an answer. */
export function isLoginWaiting(login: LoginView): boolean {
  return login.phase === 'running' && login.prompt === null && login.progress === null;
}

/** The prompt after its answer: no prompt waits until the next login step. */
export function answerPrompt(login: LoginView): LoginView {
  return { ...login, prompt: null };
}

export function readLoginMessage(message: unknown): LoginMessage | null {
  return readSocketMessage<LoginMessage>(message, LOGIN_MESSAGE_TYPES);
}
