// Fake model providers for the credential and login tests. No real provider and no real login (25.15, #186).
// - fake-oauth: an OAuth login with each pi login step, and a refresh that adds "-refreshed" to the access token.
//   A refresh token "revoked" fails.
// - fake-key: an API key provider. pi asks for the key with a secret prompt.
// Both speak the OpenAI chat completions API of the fake model server.
import { ModelRuntime } from '@earendil-works/pi-coding-agent';
import type { CreateModelRuntime, CredentialStore } from '../src/credential_file.ts';

export const FAKE_OAUTH_PROVIDER = 'fake-oauth';
export const FAKE_KEY_PROVIDER = 'fake-key';
const ONE_HOUR_MS = 3_600_000;
const UNUSED_BASE_URL = 'http://127.0.0.1:9/v1';

const FAKE_MODEL = {
  id: 'fake-model',
  name: 'Fake model',
  reasoning: false,
  input: ['text' as const],
  cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
  contextWindow: 100_000,
  maxTokens: 1000,
};

function registerFakeProviders(runtime: ModelRuntime, baseUrl: string): void {
  runtime.registerProvider(FAKE_OAUTH_PROVIDER, {
    name: 'Fake OAuth',
    baseUrl,
    api: 'openai-completions',
    models: [FAKE_MODEL],
    oauth: {
      name: 'Fake subscription',
      isSubscription: true,
      login: async (callbacks) => {
        callbacks.onAuth({ url: 'https://login.example.test/authorize', instructions: 'Open the link.' });
        callbacks.onDeviceCode({ userCode: 'ABCD-1234', verificationUri: 'https://login.example.test/device' });
        callbacks.onProgress?.('Waiting for the code.');
        const code = await callbacks.onManualCodeInput?.();
        return { access: `access-${code ?? ''}`, refresh: 'refresh-token', expires: Date.now() + ONE_HOUR_MS };
      },
      refreshToken: (credentials) => {
        if (credentials.refresh === 'revoked') {
          return Promise.reject(new Error('invalid_grant'));
        }
        return Promise.resolve({ ...credentials, access: `${credentials.access}-refreshed`, expires: Date.now() + ONE_HOUR_MS });
      },
      getApiKey: (credentials) => credentials.access,
    },
  });
  runtime.registerProvider(FAKE_KEY_PROVIDER, {
    name: 'Fake API key provider',
    baseUrl,
    api: 'openai-completions',
    // Fake model 2 has thinking levels: no "minimal", and "xhigh" but no "max".
    models: [
      FAKE_MODEL,
      {
        ...FAKE_MODEL,
        id: 'fake-model-2',
        name: 'Fake model 2',
        reasoning: true,
        thinkingLevelMap: { minimal: null, xhigh: 'xhigh' },
      },
    ],
  });
}

/** A CreateModelRuntime with the fake providers. `baseUrl` is the fake model server, when the test calls a model. */
export function createFakeRuntimeFactory(baseUrl: string = UNUSED_BASE_URL): CreateModelRuntime {
  return async (credentials) => {
    const runtime = await ModelRuntime.create({ credentials, modelsPath: null });
    registerFakeProviders(runtime, baseUrl);
    return runtime;
  };
}

export function createFakeOAuthRuntime(credentials: CredentialStore): Promise<ModelRuntime> {
  return createFakeRuntimeFactory()(credentials);
}
