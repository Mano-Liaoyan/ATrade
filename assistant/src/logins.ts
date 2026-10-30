// Provider login from the web page (docs/architecture/assistant.md 25.7.3).
// assistant calls ModelRuntime.login(provider, "oauth" | "api_key", interaction). The interaction changes each pi
// notify() event (auth_url, device_code, progress, info) into one login step. Each pi prompt() request (text, secret,
// select, manual_code) becomes a login step "prompt" with a prompt ID, and waits for the answer of the browser
// (login_answer). After the login, the new credential goes into the credential file with the name of the user.
// A login event never holds a secret: only the browser sends the API key, as an answer.
import { randomUUID } from 'node:crypto';
import type { ModelRuntime } from '@earendil-works/pi-coding-agent';
import {
  LoginCredentialStore,
  type CreateModelRuntime,
  type CredentialFile,
  type CredentialSummary,
} from './credential_file.ts';

// pi-ai is not a direct dependency, so the types come from the ModelRuntime.login parameters.
type AuthInteraction = Parameters<ModelRuntime['login']> extends [string, string, infer I, ...unknown[]] ? I : never;
type AuthPrompt = Parameters<AuthInteraction['prompt']>[0];
type AuthEvent = Parameters<AuthInteraction['notify']>[0];

export type LoginMethod = 'oauth' | 'api_key';

export interface LoginRequest {
  provider: string;
  method: LoginMethod;
  /** The credential name, for example "Anthropic API key · personal" (25.7.4). */
  name: string;
}

export interface LoginStep {
  type: 'login_step';
  step: 'auth_url' | 'device_code' | 'progress' | 'info' | 'prompt';
  message: string | null;
  url: string | null;
  user_code: string | null;
  prompt_id: string | null;
  prompt_type: 'text' | 'secret' | 'select' | 'manual_code' | null;
  options: { id: string; label: string }[] | null;
}

export type LoginEvent =
  | LoginStep
  | { type: 'login_end'; credential: CredentialSummary }
  | { type: 'error'; message: string };

const EMPTY_STEP: Omit<LoginStep, 'step'> = {
  type: 'login_step',
  message: null,
  url: null,
  user_code: null,
  prompt_id: null,
  prompt_type: null,
  options: null,
};

function toNotifyStep(event: AuthEvent): LoginStep {
  switch (event.type) {
    case 'auth_url':
      return { ...EMPTY_STEP, step: 'auth_url', url: event.url, message: event.instructions ?? null };
    case 'device_code':
      return { ...EMPTY_STEP, step: 'device_code', url: event.verificationUri, user_code: event.userCode };
    case 'progress':
      return { ...EMPTY_STEP, step: 'progress', message: event.message };
    case 'info':
      return { ...EMPTY_STEP, step: 'info', message: event.message, url: event.links?.[0]?.url ?? null };
  }
}

function toPromptStep(prompt: AuthPrompt, promptId: string): LoginStep {
  const options = prompt.type === 'select' ? prompt.options.map(({ id, label }) => ({ id, label })) : null;
  return { ...EMPTY_STEP, step: 'prompt', message: prompt.message, prompt_id: promptId, prompt_type: prompt.type, options };
}

function readErrorText(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

export interface LoginsOptions {
  file: CredentialFile;
  createRuntime: CreateModelRuntime;
}

interface PendingPrompt {
  resolve: (value: string) => void;
}

export class Logins {
  private readonly options: LoginsOptions;
  private readonly pendingPrompts = new Map<string, PendingPrompt>();

  constructor(options: LoginsOptions) {
    this.options = options;
  }

  /** Runs one login to its end. The last event is login_end or error. `signal` cancels the login. */
  async login(request: LoginRequest, emit: (event: LoginEvent) => void, signal?: AbortSignal): Promise<void> {
    try {
      const runtime = await this.options.createRuntime(new LoginCredentialStore());
      const interaction: AuthInteraction = {
        signal,
        notify: (event) => {
          emit(toNotifyStep(event));
        },
        prompt: (prompt) => this.ask(prompt, emit, signal),
      };
      const credential = await runtime.login(request.provider, request.method, interaction, { agentName: 'ATrade' });
      const id = this.options.file.add({ name: request.name, provider: request.provider, credential });
      const summary = this.options.file.find(id);
      if (summary !== undefined) {
        emit({ type: 'login_end', credential: summary });
      }
    } catch (error) {
      emit({ type: 'error', message: `The login failed: ${readErrorText(error)}` });
    }
  }

  private ask(prompt: AuthPrompt, emit: (event: LoginEvent) => void, loginSignal?: AbortSignal): Promise<string> {
    const promptId = randomUUID();
    const signals = [prompt.signal, loginSignal].filter((item) => item !== undefined);
    const signal = signals.length === 0 ? undefined : AbortSignal.any(signals);
    return new Promise<string>((resolve, reject) => {
      const onAbort = () => {
        this.pendingPrompts.delete(promptId);
        reject(new Error('The login was cancelled.'));
      };
      if (signal?.aborted === true) {
        onAbort();
        return;
      }
      signal?.addEventListener('abort', onAbort, { once: true });
      this.pendingPrompts.set(promptId, {
        resolve: (value) => {
          signal?.removeEventListener('abort', onAbort);
          resolve(value);
        },
      });
      emit(toPromptStep(prompt, promptId));
    });
  }

  /** Answers a prompt step. False when no login waits for this prompt. */
  answer(promptId: string, value: string): boolean {
    const pending = this.pendingPrompts.get(promptId);
    if (pending === undefined) {
      return false;
    }
    this.pendingPrompts.delete(promptId);
    pending.resolve(value);
    return true;
  }
}
