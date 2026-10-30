// Connects a pi ModelRuntime to the fake model server. The provider "fake" speaks the OpenAI chat completions API.
// The test credentials exist only here (docs/architecture/assistant.md 25.14). They are not in .env or PostgreSQL.
import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { ModelRuntime } from '@earendil-works/pi-coding-agent';
import type { OpenModel } from '../src/model_selection.ts';

/** Credential ID → credential name, for the conversation tests. The credential file tests use fake_providers.ts. */
export const FAKE_CREDENTIAL_NAMES: Readonly<Record<string, string>> = {
  'fake-key-1': 'Fake API key · first',
  'fake-key-2': 'Fake API key · second',
};

async function createFakeModelRuntime(baseUrl: string, workDir: string): Promise<ModelRuntime> {
  const runtimeDir = path.join(workDir, 'model-runtime');
  mkdirSync(runtimeDir, { recursive: true });
  const modelsPath = path.join(runtimeDir, 'models.json');
  const providers = {
    fake: {
      baseUrl,
      api: 'openai-completions',
      apiKey: 'fake-key',
      models: [{ id: 'fake-model' }, { id: 'fake-model-2' }],
    },
  };
  writeFileSync(modelsPath, JSON.stringify({ providers }));
  return ModelRuntime.create({ authPath: path.join(runtimeDir, 'auth.json'), modelsPath });
}

export async function openFakeModel(baseUrl: string, workDir: string) {
  const modelRuntime = await createFakeModelRuntime(baseUrl, workDir);
  const model = modelRuntime.getModel('fake', 'fake-model');
  if (model === undefined) {
    throw new Error('The fake model is not in the model runtime.');
  }
  return { modelRuntime, model };
}

/** An OpenModel function for the fake model server, with the test credentials of FAKE_CREDENTIAL_NAMES. */
export async function createFakeOpenModel(baseUrl: string, workDir: string): Promise<OpenModel> {
  const modelRuntime = await createFakeModelRuntime(baseUrl, workDir);
  return (selection) => {
    const credentialName = FAKE_CREDENTIAL_NAMES[selection.credentialId];
    const model = modelRuntime.getModel(selection.provider, selection.model);
    if (credentialName === undefined || model === undefined) {
      return Promise.reject(new Error(`The credential ${selection.credentialId} does not exist.`));
    }
    return Promise.resolve({ modelRuntime, model, credentialName });
  };
}
