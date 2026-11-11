import { describe, expect, test } from 'vite-plus/test';
import {
  addLoginMessage,
  answerPrompt,
  describeCredentialKind,
  describeCredentialState,
  formatKey,
  isAnthropicSubscription,
  isLoginWaiting,
  listLoginProviders,
  NO_LOGIN,
  STARTED_LOGIN,
  type Credential,
  type LoginStepMessage,
  type Provider,
} from './credentials';

const API_KEY: Credential = {
  id: 'c1',
  name: 'Anthropic API key · personal',
  provider: 'anthropic',
  type: 'api_key',
  key_last4: '7a9f',
  state: 'ready',
  state_message: null,
};

function step(overrides: Partial<LoginStepMessage>): LoginStepMessage {
  return {
    type: 'login_step',
    step: 'progress',
    message: null,
    url: null,
    user_code: null,
    prompt_id: null,
    prompt_type: null,
    options: null,
    ...overrides,
  };
}

describe('the credential columns', () => {
  test('an API key shows only its last 4 characters', () => {
    expect(formatKey(API_KEY)).toBe('••••7a9f');
    expect(formatKey({ ...API_KEY, type: 'oauth', key_last4: null })).toBe('');
  });

  test('the kind is a subscription, an API key, or the Claude Code login', () => {
    expect(describeCredentialKind('oauth')).toBe('Subscription');
    expect(describeCredentialKind('api_key')).toBe('API key');
    expect(describeCredentialKind('claude_code')).toBe('Claude Code login');
  });

  test("pi's Anthropic subscription shows its risk, and the Claude Code login that is not ready gives the command", () => {
    const subscription: Credential = { ...API_KEY, type: 'oauth', key_last4: null };
    const claudeCode: Credential = {
      ...API_KEY,
      provider: 'claude-code',
      type: 'claude_code',
      key_last4: null,
      state: 'failed',
      state_message: 'Run this command on the server: claude auth login',
    };

    expect(isAnthropicSubscription('anthropic', 'oauth')).toBe(true);
    expect(isAnthropicSubscription('anthropic', 'api_key')).toBe(false);
    expect(describeCredentialState(subscription)).toMatchObject({
      kind: 'warning',
      label: expect.stringContaining('Anthropic does not permit this login') as string,
    });
    expect(describeCredentialState(claudeCode)).toEqual({
      kind: 'error',
      label: 'Run this command on the server: claude auth login',
    });
  });

  test('a ready credential is a success, and a failed refresh is an error with its reason', () => {
    expect(describeCredentialState(API_KEY)).toEqual({ kind: 'success', label: 'Ready' });
    expect(
      describeCredentialState({ ...API_KEY, state: 'failed', state_message: 'OAuth refresh failed for anthropic' }),
    ).toEqual({ kind: 'error', label: 'Log in again: OAuth refresh failed for anthropic' });
  });
});

describe('the providers of a login method', () => {
  const providers: Provider[] = [
    { id: 'anthropic', name: 'Anthropic', login_methods: ['oauth', 'api_key'], models: [] },
    { id: 'google', name: 'Google', login_methods: ['api_key'], models: [] },
  ];

  test('a subscription login lists only the providers with OAuth', () => {
    expect(listLoginProviders(providers, 'oauth')).toEqual([{ value: 'anthropic', label: 'Anthropic' }]);
    expect(listLoginProviders(providers, 'api_key')).toEqual([
      { value: 'anthropic', label: 'Anthropic' },
      { value: 'google', label: 'Google' },
    ]);
  });
});

describe('the login steps', () => {
  test('the login waits while it has no prompt and no progress: after the start and after an answer', () => {
    const prompted = addLoginMessage(STARTED_LOGIN, step({ step: 'prompt', prompt_id: 'p1', prompt_type: 'secret' }));

    expect(isLoginWaiting(NO_LOGIN)).toBe(false);
    expect(isLoginWaiting(STARTED_LOGIN)).toBe(true);
    expect(isLoginWaiting(prompted)).toBe(false);
    expect(isLoginWaiting(answerPrompt(prompted))).toBe(true);
    expect(isLoginWaiting(addLoginMessage(STARTED_LOGIN, step({ step: 'progress', message: 'Waiting.' })))).toBe(false);
  });

  test('the link, the device code, and the progress stay, and a prompt waits for its answer', () => {
    let login = addLoginMessage(NO_LOGIN, step({ step: 'auth_url', url: 'https://login.example.test' }));
    login = addLoginMessage(login, step({ step: 'device_code', user_code: 'ABCD-1234', url: 'https://x.test/device' }));
    login = addLoginMessage(login, step({ step: 'progress', message: 'Waiting.' }));
    login = addLoginMessage(login, step({ step: 'prompt', prompt_id: 'p1', prompt_type: 'manual_code', message: 'Code' }));

    expect(login.phase).toBe('running');
    expect(login.authUrl).toBe('https://login.example.test');
    expect(login.deviceCode).toEqual({ userCode: 'ABCD-1234', url: 'https://x.test/device' });
    expect(login.progress).toBe('Waiting.');
    expect(login.prompt?.prompt_id).toBe('p1');
  });

  test('the end of the login closes the steps, and an error keeps its message', () => {
    const running = addLoginMessage(NO_LOGIN, step({ step: 'prompt', prompt_id: 'p1', prompt_type: 'secret' }));

    expect(addLoginMessage(running, { type: 'login_end', credential: API_KEY })).toEqual(NO_LOGIN);
    expect(addLoginMessage(running, { type: 'error', message: 'The login failed: invalid key' })).toMatchObject({
      phase: 'failed',
      error: 'The login failed: invalid key',
      prompt: null,
    });
  });
});
