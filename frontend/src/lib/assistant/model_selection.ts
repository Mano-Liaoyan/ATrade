// The provider, model, and credential Selects of the assistant side column, and the Send button
// (docs/architecture/assistant.md 25.8.2, 25.12.1). The browser sends the selection with each prompt, so a change
// applies to the next message.
import type { SelectItem } from '#lib/foundation/carbon';
import type { Credential, Provider } from './credentials';

export interface ModelSelection {
  provider: string;
  model: string;
  credentialId: string;
}

export interface LastModel {
  provider: string | null;
  model: string | null;
  credentialName: string | null;
}

const NO_SELECTION: ModelSelection = { provider: '', model: '', credentialId: '' };

/** The first model and the first credential of a provider. */
export function changeProvider(providers: readonly Provider[], credentials: readonly Credential[], provider: string): ModelSelection {
  const model = providers.find((item) => item.id === provider)?.models[0]?.id ?? '';
  const credentialId = credentials.find((item) => item.provider === provider)?.id ?? '';
  return { provider, model, credentialId };
}

/** The last model and credential of the conversation, else the first credential and the first model of its provider. */
export function findDefaultSelection(
  providers: readonly Provider[],
  credentials: readonly Credential[],
  last: LastModel,
): ModelSelection {
  const lastCredential = credentials.find((item) => item.name === last.credentialName && item.provider === last.provider);
  const lastProvider = providers.find((item) => item.id === last.provider);
  if (lastCredential !== undefined && lastProvider !== undefined) {
    const hasModel = lastProvider.models.some((model) => model.id === last.model);
    return {
      provider: lastProvider.id,
      model: hasModel ? (last.model ?? '') : (lastProvider.models[0]?.id ?? ''),
      credentialId: lastCredential.id,
    };
  }
  const first = credentials.find((item) => providers.some((provider) => provider.id === item.provider));
  return first === undefined ? NO_SELECTION : changeProvider(providers, credentials, first.provider);
}

export interface SelectionItems {
  providers: SelectItem<string>[];
  models: SelectItem<string>[];
  credentials: SelectItem<string>[];
}

/** Only a provider with a credential can answer, so the provider Select lists only these. */
export function listSelectItems(
  providers: readonly Provider[],
  credentials: readonly Credential[],
  provider: string,
): SelectionItems {
  return {
    providers: providers
      .filter((item) => credentials.some((credential) => credential.provider === item.id))
      .map((item) => ({ value: item.id, label: item.name })),
    models: (providers.find((item) => item.id === provider)?.models ?? []).map((model) => ({ value: model.id, label: model.name })),
    credentials: credentials
      .filter((credential) => credential.provider === provider)
      .map((credential) => ({ value: credential.id, label: credential.name })),
  };
}

export interface SendState {
  hasConversation: boolean;
  hasCredential: boolean;
  isConnected: boolean;
  isRunning: boolean;
}

export interface SendButton {
  action: 'send' | 'stop';
  label: string;
  /** Null for an enabled button. */
  disabledReason: string | null;
}

/** "Send" becomes "Stop" while the AI assistant runs. A disabled button says why. */
export function describeSendButton(state: SendState): SendButton {
  if (state.isRunning) {
    return { action: 'stop', label: 'Stop', disabledReason: null };
  }
  const disabledReason = !state.hasConversation
    ? 'Start a new conversation to send.'
    : !state.hasCredential
      ? 'Add a credential to send.'
      : !state.isConnected
        ? 'Connecting to the AI assistant.'
        : null;
  return { action: 'send', label: 'Send', disabledReason };
}
