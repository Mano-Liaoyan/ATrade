// The provider, model, and credential that the user selects for a conversation (docs/architecture/assistant.md 25.7.1).
import type { ModelRuntime } from '@earendil-works/pi-coding-agent';

export interface ModelSelection {
  provider: string;
  model: string;
  credentialId: string;
}

export interface OpenedModel {
  /** A ModelRuntime with only the selected credential (25.7.2). */
  modelRuntime: ModelRuntime;
  model: NonNullable<ReturnType<ModelRuntime['getModel']>>;
  credentialName: string;
}

/** Opens the selected model. Rejects when the credential or the model does not exist. */
export type OpenModel = (selection: ModelSelection) => Promise<OpenedModel>;

/** The OpenModel of the service until the credential store exists (#183): no credential exists. */
export const openNoModel: OpenModel = (selection) =>
  Promise.reject(new Error(`The credential ${selection.credentialId} does not exist.`));
