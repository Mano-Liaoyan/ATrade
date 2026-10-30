// The credentials of the AI assistant (docs/architecture/assistant.md 25.7.2, ADR 0005).
// All credentials are in one JSON file in the volume atrade-assistant-pi, mode 0600. One provider can have many
// credentials. pi's own auth.json keeps only 1 credential for each provider, so ATrade keeps this file.
//
// File: {"credentials": [{id, name, provider, credential, state, state_message}]}. `credential` is the pi credential
// ({type: "api_key", key} or {type: "oauth", access, refresh, expires, ...}).
//
// A conversation gets a ModelRuntime with a SelectedCredentialStore: pi sees only the selected credential. An OAuth
// refresh writes the new token back to the same entry. A failed refresh sets the state "failed": the user must log in
// again. A good refresh sets the state "ready" again.
import { randomUUID } from 'node:crypto';
import { chmodSync, existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { ModelRuntime, type CreateModelRuntimeOptions } from '@earendil-works/pi-coding-agent';

export type CredentialStore = NonNullable<CreateModelRuntimeOptions['credentials']>;
export type Credential = NonNullable<Awaited<ReturnType<CredentialStore['read']>>>;
type CredentialList = Awaited<ReturnType<CredentialStore['list']>>;
export type CredentialState = 'ready' | 'failed';

/** Creates a ModelRuntime that reads its credentials only from `credentials`. Tests add fake providers. */
export type CreateModelRuntime = (credentials: CredentialStore) => Promise<ModelRuntime>;

/** No models.json: the providers and the models come from pi only (25.7.1). */
export const createModelRuntime: CreateModelRuntime = (credentials) =>
  ModelRuntime.create({ credentials, modelsPath: null });

const FILE_MODE = 0o600;
const KEY_SUFFIX_LENGTH = 4;

interface StoredCredential {
  id: string;
  name: string;
  provider: string;
  credential: Credential;
  state: CredentialState;
  state_message: string | null;
}

export interface NewCredential {
  name: string;
  provider: string;
  credential: Credential;
}

/** A credential without its secret, for the Credentials dialog (25.7.4). */
export interface CredentialSummary {
  id: string;
  name: string;
  provider: string;
  type: Credential['type'];
  /** The last 4 characters of an API key. Null for an OAuth credential. */
  key_last4: string | null;
  state: CredentialState;
  state_message: string | null;
}

function toSummary(entry: StoredCredential): CredentialSummary {
  const key = entry.credential.type === 'api_key' ? (entry.credential.key ?? '') : null;
  return {
    id: entry.id,
    name: entry.name,
    provider: entry.provider,
    type: entry.credential.type,
    key_last4: key === null ? null : key.slice(-KEY_SUFFIX_LENGTH),
    state: entry.state,
    state_message: entry.state_message,
  };
}

function readErrorText(error: unknown): string {
  const cause = error instanceof Error && error.cause instanceof Error ? ` (${error.cause.message})` : '';
  return `${error instanceof Error ? error.message : String(error)}${cause}`;
}

export class CredentialFile {
  private readonly filePath: string;
  /** Serializes each read-modify-write that waits for pi (an OAuth refresh). */
  private queue: Promise<unknown> = Promise.resolve();

  constructor(filePath: string) {
    this.filePath = filePath;
  }

  private readAll(): StoredCredential[] {
    if (!existsSync(this.filePath)) {
      return [];
    }
    return (JSON.parse(readFileSync(this.filePath, 'utf8')) as { credentials: StoredCredential[] }).credentials;
  }

  /** Writes a new file with mode 0600, then renames it, so a crash never leaves half a file. */
  private writeAll(credentials: StoredCredential[]): void {
    mkdirSync(path.dirname(this.filePath), { recursive: true });
    const temporaryPath = `${this.filePath}.${randomUUID()}.tmp`;
    writeFileSync(temporaryPath, JSON.stringify({ credentials }), { mode: FILE_MODE });
    chmodSync(temporaryPath, FILE_MODE);
    renameSync(temporaryPath, this.filePath);
  }

  list(): CredentialSummary[] {
    return this.readAll().map(toSummary);
  }

  find(id: string): CredentialSummary | undefined {
    const entry = this.readAll().find((stored) => stored.id === id);
    return entry === undefined ? undefined : toSummary(entry);
  }

  read(id: string): Credential | undefined {
    return this.readAll().find((stored) => stored.id === id)?.credential;
  }

  /** Adds a credential and returns its ID. */
  add(newCredential: NewCredential): string {
    const id = randomUUID();
    this.writeAll([...this.readAll(), { id, ...newCredential, state: 'ready', state_message: null }]);
    return id;
  }

  /** Deletes a credential. False when it does not exist. */
  delete(id: string): boolean {
    const credentials = this.readAll();
    const kept = credentials.filter((stored) => stored.id !== id);
    if (kept.length === credentials.length) {
      return false;
    }
    this.writeAll(kept);
    return true;
  }

  private update(id: string, change: Partial<StoredCredential>): void {
    this.writeAll(this.readAll().map((stored) => (stored.id === id ? { ...stored, ...change } : stored)));
  }

  /** pi's serialized write for one credential. A failure of `fn` (a failed refresh) sets the state "failed". */
  modify(id: string, fn: (current: Credential | undefined) => Promise<Credential | undefined>) {
    const operation = this.queue.then(async () => {
      let next: Credential | undefined;
      try {
        next = await fn(this.read(id));
      } catch (error) {
        this.update(id, { state: 'failed', state_message: readErrorText(error) });
        throw error;
      }
      if (next !== undefined && this.read(id) !== undefined) {
        this.update(id, { credential: next, state: 'ready', state_message: null });
      }
      return next ?? this.read(id);
    });
    this.queue = operation.catch(() => undefined);
    return operation;
  }
}

/** The pi CredentialStore of one conversation: only the selected credential, for its provider. */
export class SelectedCredentialStore implements CredentialStore {
  private readonly file: CredentialFile;
  private readonly id: string;
  private readonly provider: string;

  constructor(file: CredentialFile, id: string) {
    const summary = file.find(id);
    if (summary === undefined) {
      throw new Error(`The credential ${id} does not exist.`);
    }
    this.file = file;
    this.id = id;
    this.provider = summary.provider;
  }

  read(providerId: string): Promise<Credential | undefined> {
    return Promise.resolve(providerId === this.provider ? this.file.read(this.id) : undefined);
  }

  list(): Promise<CredentialList> {
    const credential = this.file.read(this.id);
    return Promise.resolve(credential === undefined ? [] : [{ providerId: this.provider, type: credential.type }]);
  }

  modify(
    providerId: string,
    fn: (current: Credential | undefined) => Promise<Credential | undefined>,
  ): Promise<Credential | undefined> {
    if (providerId !== this.provider) {
      return Promise.reject(new Error(`The selected credential is for ${this.provider}, not for ${providerId}.`));
    }
    return this.file.modify(this.id, fn);
  }

  /** pi deletes a credential only at logout. ATrade deletes credentials only through the Credentials dialog. */
  delete(): Promise<void> {
    return Promise.resolve();
  }
}

/** A CredentialStore in memory for a login: pi writes the new credential here, then ATrade adds it to the file. */
export class LoginCredentialStore implements CredentialStore {
  private readonly credentials = new Map<string, Credential>();

  read(providerId: string): Promise<Credential | undefined> {
    return Promise.resolve(this.credentials.get(providerId));
  }

  list(): Promise<CredentialList> {
    return Promise.resolve(
      [...this.credentials].map(([providerId, credential]) => ({ providerId, type: credential.type })),
    );
  }

  async modify(
    providerId: string,
    fn: (current: Credential | undefined) => Promise<Credential | undefined>,
  ): Promise<Credential | undefined> {
    const next = await fn(this.credentials.get(providerId));
    if (next !== undefined) {
      this.credentials.set(providerId, next);
    }
    return this.credentials.get(providerId);
  }

  delete(providerId: string): Promise<void> {
    this.credentials.delete(providerId);
    return Promise.resolve();
  }
}
