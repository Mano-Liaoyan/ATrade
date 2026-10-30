// Connects a pi ModelRuntime to the fake model server. The provider "fake" speaks the OpenAI chat completions API.
import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { ModelRuntime } from '@earendil-works/pi-coding-agent';

export async function openFakeModel(baseUrl: string, workDir: string) {
  const runtimeDir = path.join(workDir, 'model-runtime');
  mkdirSync(runtimeDir, { recursive: true });
  const modelsPath = path.join(runtimeDir, 'models.json');
  const providers = {
    fake: { baseUrl, api: 'openai-completions', apiKey: 'fake-key', models: [{ id: 'fake-model' }] },
  };
  writeFileSync(modelsPath, JSON.stringify({ providers }));
  const modelRuntime = await ModelRuntime.create({ authPath: path.join(runtimeDir, 'auth.json'), modelsPath });
  const model = modelRuntime.getModel('fake', 'fake-model');
  if (model === undefined) {
    throw new Error('The fake model is not in the model runtime.');
  }
  return { modelRuntime, model };
}
