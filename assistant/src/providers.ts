// The providers and models for the model selection (docs/architecture/assistant.md 25.7.1), and the model of one run.
// The providers come from pi (ModelRuntime.getProviders()), not from a fixed list. The models of a provider come from
// ModelRuntime.getAvailable(provider) with the stored credentials of that provider. A provider without a credential
// has no models.
import {
  LoginCredentialStore,
  SelectedCredentialStore,
  type CreateModelRuntime,
  type CredentialFile,
} from './credential_file.ts';
import type { LoginMethod } from './logins.ts';
import { listThinkingLevels, type OpenModel, type ThinkingLevel } from './model_selection.ts';

export interface ProviderSummary {
  id: string;
  name: string;
  /** The login methods of pi for this provider: "oauth" (a subscription login) and "api_key". */
  login_methods: LoginMethod[];
  /** `thinking_levels`: the thinking levels of the model (only "off" for a model without reasoning). */
  models: { id: string; name: string; thinking_levels: ThinkingLevel[] }[];
}

async function readModels(
  file: CredentialFile,
  createRuntime: CreateModelRuntime,
  providerId: string,
): Promise<ProviderSummary['models']> {
  const models = new Map<string, ProviderSummary['models'][number]>();
  for (const credential of file.list().filter((stored) => stored.provider === providerId)) {
    const runtime = await createRuntime(new SelectedCredentialStore(file, credential.id));
    for (const model of await runtime.getAvailable(providerId)) {
      models.set(model.id, { id: model.id, name: model.name, thinking_levels: listThinkingLevels(model) });
    }
  }
  return [...models.values()];
}

/** The providers with at least one login method, in the order of pi. */
export async function listProviders(file: CredentialFile, createRuntime: CreateModelRuntime): Promise<ProviderSummary[]> {
  const runtime = await createRuntime(new LoginCredentialStore());
  const providers: ProviderSummary[] = [];
  for (const provider of runtime.getProviders()) {
    const loginMethods: LoginMethod[] = [];
    if (provider.auth.oauth !== undefined) {
      loginMethods.push('oauth');
    }
    if (provider.auth.apiKey?.login !== undefined) {
      loginMethods.push('api_key');
    }
    if (loginMethods.length > 0) {
      providers.push({
        id: provider.id,
        name: provider.name,
        login_methods: loginMethods,
        models: await readModels(file, createRuntime, provider.id),
      });
    }
  }
  return providers;
}

/** The OpenModel of the service: a ModelRuntime with only the selected credential of the file (25.7.2). */
export function openStoredModel(file: CredentialFile, createRuntime: CreateModelRuntime): OpenModel {
  return async (selection) => {
    const credential = file.find(selection.credentialId);
    if (credential === undefined) {
      throw new Error(`The credential ${selection.credentialId} does not exist.`);
    }
    if (credential.provider !== selection.provider) {
      throw new Error(`The credential ${credential.name} is for ${credential.provider}, not for ${selection.provider}.`);
    }
    const modelRuntime = await createRuntime(new SelectedCredentialStore(file, credential.id));
    const model = modelRuntime.getModel(selection.provider, selection.model);
    if (model === undefined) {
      throw new Error(`The model ${selection.model} of ${selection.provider} does not exist.`);
    }
    return { modelRuntime, model, credentialName: credential.name };
  };
}
