// Provider login from the web page (docs/architecture/assistant.md 25.7.3) and the provider list (25.7.1).
// The login flows are fakes. The first real login is #186.
import { mkdtempSync, readFileSync, rmSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { afterEach, beforeEach, describe, expect, test } from 'vite-plus/test';
import { CredentialFile, createModelRuntime } from '../src/credential_file.ts';
import { Logins, type LoginEvent } from '../src/logins.ts';
import { listProviders, openStoredModel } from '../src/providers.ts';
import { createFakeRuntimeFactory, FAKE_KEY_PROVIDER, FAKE_OAUTH_PROVIDER } from './fake_providers.ts';

let workDir: string;
let file: CredentialFile;
let logins: Logins;

beforeEach(() => {
  workDir = mkdtempSync(path.join(tmpdir(), 'atrade-logins-'));
  file = new CredentialFile(path.join(workDir, 'credentials.json'));
  logins = new Logins({ file, createRuntime: createFakeRuntimeFactory(), deviceIdFile: path.join(workDir, 'device-id') });
});

afterEach(() => {
  rmSync(workDir, { recursive: true, force: true });
});

/** Runs a login. Each prompt step gets the next answer of `answers`. */
async function loginWith(
  request: { provider: string; method: 'oauth' | 'api_key'; name: string },
  answers: string[],
): Promise<LoginEvent[]> {
  const events: LoginEvent[] = [];
  await logins.login(request, (event) => {
    events.push(event);
    if (event.type === 'login_step' && event.step === 'prompt' && event.prompt_id !== null) {
      expect(logins.answer(event.prompt_id, answers.shift() ?? '')).toBe(true);
    }
  });
  return events;
}

describe('a subscription login', () => {
  test('sends one login step for each pi event and waits for the pasted code', async () => {
    const events = await loginWith({ provider: FAKE_OAUTH_PROVIDER, method: 'oauth', name: 'Personal' }, ['CODE42']);

    const steps = events.filter((event) => event.type === 'login_step');
    expect(steps.map((step) => step.step)).toEqual(['auth_url', 'device_code', 'progress', 'prompt']);
    expect(steps[0]).toMatchObject({ url: 'https://login.example.test/authorize', message: 'Open the link.' });
    expect(steps[1]).toMatchObject({ user_code: 'ABCD-1234', url: 'https://login.example.test/device' });
    expect(steps[3]).toMatchObject({ prompt_type: 'manual_code' });
    expect(events.at(-1)).toMatchObject({
      type: 'login_end',
      credential: { name: 'Personal', provider: FAKE_OAUTH_PROVIDER, type: 'oauth', key_last4: null, state: 'ready' },
    });
    expect(readFileSync(path.join(workDir, 'credentials.json'), 'utf8')).toContain('access-CODE42');
  });

  test('a cancelled login adds no credential', async () => {
    const controller = new AbortController();
    const events: LoginEvent[] = [];
    await logins.login(
      { provider: FAKE_OAUTH_PROVIDER, method: 'oauth', name: 'Cancelled' },
      (event) => {
        events.push(event);
        if (event.type === 'login_step' && event.step === 'prompt') {
          controller.abort();
        }
      },
      controller.signal,
    );

    expect(events.at(-1)?.type).toBe('error');
    expect(file.list()).toEqual([]);
  });
});

describe('an API key login', () => {
  test('asks for the key with a secret prompt and shows only its last 4 characters', async () => {
    const events = await loginWith({ provider: FAKE_KEY_PROVIDER, method: 'api_key', name: 'Work' }, ['sk-test-7a9f']);

    expect(events.find((event) => event.type === 'login_step')).toMatchObject({ step: 'prompt', prompt_type: 'secret' });
    expect(JSON.stringify(events)).not.toContain('sk-test');
    expect(events.at(-1)).toMatchObject({ type: 'login_end', credential: { type: 'api_key', key_last4: '7a9f' } });
  });

  test('an answer to an unknown prompt is refused', () => {
    expect(logins.answer('no-such-prompt', 'x')).toBe(false);
  });
});

describe('the provider list', () => {
  test('comes from pi, and a provider without a credential has no models', async () => {
    file.add({ name: 'Key', provider: FAKE_KEY_PROVIDER, credential: { type: 'api_key', key: 'k-1234' } });

    const providers = await listProviders(file, createFakeRuntimeFactory());

    const fakeKey = providers.find((provider) => provider.id === FAKE_KEY_PROVIDER);
    expect(fakeKey?.models.map((model) => model.id)).toEqual(['fake-model', 'fake-model-2']);
    expect(fakeKey?.login_methods).toEqual(['api_key']);
    expect(providers.find((provider) => provider.id === FAKE_OAUTH_PROVIDER)).toMatchObject({
      login_methods: ['oauth'],
      models: [],
    });
  });

  test('has the pi providers, and Google has only the API key method', async () => {
    const providers = await listProviders(file, createModelRuntime);

    expect(providers.map((provider) => provider.id)).toEqual(expect.arrayContaining(['anthropic', 'openai', 'google']));
    expect(providers.find((provider) => provider.id === 'google')?.login_methods).toEqual(['api_key']);
    expect(providers.find((provider) => provider.id === 'anthropic')?.login_methods).toEqual(['oauth', 'api_key']);
    expect(providers.every((provider) => provider.models.length === 0)).toBe(true);
  });
});

describe('the model of a conversation', () => {
  test('opens with the stored credential and its name', async () => {
    const id = file.add({ name: 'Key · work', provider: FAKE_KEY_PROVIDER, credential: { type: 'api_key', key: 'k-1' } });
    const openModel = openStoredModel(file, createFakeRuntimeFactory());

    const opened = await openModel({ provider: FAKE_KEY_PROVIDER, model: 'fake-model-2', credentialId: id });

    expect(opened.credentialName).toBe('Key · work');
    expect(opened.model.id).toBe('fake-model-2');
    expect((await opened.modelRuntime.getAuth(FAKE_KEY_PROVIDER))?.auth.apiKey).toBe('k-1');
  });

  test('refuses a credential that does not exist or is for another provider', async () => {
    const id = file.add({ name: 'Key', provider: FAKE_KEY_PROVIDER, credential: { type: 'api_key', key: 'k-1' } });
    const openModel = openStoredModel(file, createFakeRuntimeFactory());

    await expect(openModel({ provider: FAKE_KEY_PROVIDER, model: 'fake-model', credentialId: 'missing' })).rejects.toThrow(
      'The credential missing does not exist.',
    );
    await expect(openModel({ provider: FAKE_OAUTH_PROVIDER, model: 'fake-model', credentialId: id })).rejects.toThrow(
      'is for fake-key',
    );
  });
});

describe('the device ID of the installation', () => {
  // "Sign in with ChatGPT" refuses a login without a device ID (UUID). pi's own CLI passes getDeviceId to login().
  test('each login gets the same UUID, also after a restart, and the file has mode 0600', async () => {
    const deviceIdFile = path.join(workDir, 'device-id');
    const seenIds: (string | undefined)[] = [];
    const createRuntime = createFakeRuntimeFactory();
    const recordingRuntime: typeof createRuntime = async (credentials) => {
      const runtime = await createRuntime(credentials);
      const login = runtime.login.bind(runtime);
      runtime.login = (provider, method, interaction, options) => {
        seenIds.push(options?.getDeviceId?.());
        return login(provider, method, interaction, options);
      };
      return runtime;
    };
    const request = { provider: FAKE_KEY_PROVIDER, method: 'api_key' as const, name: 'Key' };
    const answer = (target: Logins) => (event: LoginEvent) => {
      if (event.type === 'login_step' && event.prompt_id !== null) {
        target.answer(event.prompt_id, 'k-1');
      }
    };

    const first = new Logins({ file, createRuntime: recordingRuntime, deviceIdFile });
    await first.login(request, answer(first));
    const restarted = new Logins({ file, createRuntime: recordingRuntime, deviceIdFile });
    await restarted.login(request, answer(restarted));

    expect(seenIds[0]).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/);
    expect(seenIds[1]).toBe(seenIds[0]);
    expect(statSync(deviceIdFile).mode & 0o777).toBe(0o600);
  });
});
