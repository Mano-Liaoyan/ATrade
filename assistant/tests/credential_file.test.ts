// The credential file of the assistant service (docs/architecture/assistant.md 25.7.2). No real provider: the OAuth
// provider is a fake that the test registers in the model runtime.
import { mkdtempSync, readFileSync, rmSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { afterEach, beforeEach, describe, expect, test } from 'vite-plus/test';
import { CredentialFile, SelectedCredentialStore } from '../src/credential_file.ts';
import { createFakeOAuthRuntime, FAKE_OAUTH_PROVIDER } from './fake_providers.ts';

const FILE_MODE_BITS = 0o777;

let workDir: string;
let file: CredentialFile;

beforeEach(() => {
  workDir = mkdtempSync(path.join(tmpdir(), 'atrade-credentials-'));
  file = new CredentialFile(path.join(workDir, 'credentials.json'));
});

afterEach(() => {
  rmSync(workDir, { recursive: true, force: true });
});

function readStored(): { credentials: { id: string; credential: Record<string, unknown> }[] } {
  return JSON.parse(readFileSync(path.join(workDir, 'credentials.json'), 'utf8')) as {
    credentials: { id: string; credential: Record<string, unknown> }[];
  };
}

describe('the credential file', () => {
  test('keeps 2 credentials of one provider in one file with mode 0600', () => {
    file.add({ name: 'Personal', provider: 'anthropic', credential: { type: 'api_key', key: 'sk-first-1234' } });
    file.add({ name: 'Work', provider: 'anthropic', credential: { type: 'api_key', key: 'sk-second-5678' } });

    expect(statSync(path.join(workDir, 'credentials.json')).mode & FILE_MODE_BITS).toBe(0o600);
    expect(readStored().credentials.map((entry) => entry.credential.key)).toEqual(['sk-first-1234', 'sk-second-5678']);
  });

  test('lists the credentials with only the last 4 characters of an API key', () => {
    const id = file.add({ name: 'Personal', provider: 'google', credential: { type: 'api_key', key: 'AIza-secret-9876' } });

    expect(file.list()).toEqual([
      { id, name: 'Personal', provider: 'google', type: 'api_key', key_last4: '9876', state: 'ready', state_message: null },
    ]);
    expect(JSON.stringify(file.list())).not.toContain('secret');
  });

  test('deletes one credential and keeps the other', () => {
    const first = file.add({ name: 'A', provider: 'xai', credential: { type: 'api_key', key: 'key-aaaa' } });
    const second = file.add({ name: 'B', provider: 'xai', credential: { type: 'api_key', key: 'key-bbbb' } });

    expect(file.delete(first)).toBe(true);
    expect(file.delete(first)).toBe(false);
    expect(file.list().map((entry) => entry.id)).toEqual([second]);
  });
});

describe('the model runtime of one conversation', () => {
  function addTwoOAuthCredentials(expires: number): { first: string; second: string } {
    const credential = (access: string) => ({ type: 'oauth' as const, access, refresh: `${access}-refresh`, expires });
    return {
      first: file.add({ name: 'First', provider: FAKE_OAUTH_PROVIDER, credential: credential('first-token') }),
      second: file.add({ name: 'Second', provider: FAKE_OAUTH_PROVIDER, credential: credential('second-token') }),
    };
  }

  test('sees only the selected credential', async () => {
    const { second } = addTwoOAuthCredentials(Date.now() + 3_600_000);
    const runtime = await createFakeOAuthRuntime(new SelectedCredentialStore(file, second));

    expect(await runtime.listCredentials()).toEqual([{ providerId: FAKE_OAUTH_PROVIDER, type: 'oauth' }]);
    expect((await runtime.getAuth(FAKE_OAUTH_PROVIDER))?.auth.apiKey).toBe('second-token');
  });

  test('writes the refreshed token back to the same file and keeps the other credential', async () => {
    const { first } = addTwoOAuthCredentials(Date.now() - 1000);
    const runtime = await createFakeOAuthRuntime(new SelectedCredentialStore(file, first));

    expect((await runtime.getAuth(FAKE_OAUTH_PROVIDER))?.auth.apiKey).toBe('first-token-refreshed');

    const stored = readStored().credentials.map((entry) => entry.credential.access);
    expect(stored).toEqual(['first-token-refreshed', 'second-token']);
    expect(statSync(path.join(workDir, 'credentials.json')).mode & FILE_MODE_BITS).toBe(0o600);
  });

  test('marks the credential as failed when the refresh fails', async () => {
    const id = file.add({
      name: 'Broken',
      provider: FAKE_OAUTH_PROVIDER,
      credential: { type: 'oauth', access: 'old', refresh: 'revoked', expires: Date.now() - 1000 },
    });
    const runtime = await createFakeOAuthRuntime(new SelectedCredentialStore(file, id));

    await expect(runtime.getAuth(FAKE_OAUTH_PROVIDER)).rejects.toThrow();

    expect(file.list()[0]?.state).toBe('failed');
    expect(file.list()[0]?.state_message).toContain('refresh');
  });
});
