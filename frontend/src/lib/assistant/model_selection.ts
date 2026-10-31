// The model, thinking, provider, and credential Selects of the assistant side column, and the Send button
// (docs/architecture/assistant.md 25.8.2, 25.12.1). The browser sends the selection with each prompt, so a change
// applies to the next message.
import type { components } from '#lib/api';
import type { SelectItem } from '#lib/foundation/carbon';
import type { Credential, Provider } from './credentials';

/** The thinking levels of pi, in its order. */
export type ThinkingLevel = components['schemas']['ThinkingLevel'];

const THINKING_LEVEL_LABELS: Record<ThinkingLevel, string> = {
  off: 'Off',
  minimal: 'Minimal',
  low: 'Low',
  medium: 'Medium',
  high: 'High',
  xhigh: 'Extra high',
  max: 'Max',
};
const THINKING_LEVELS = Object.keys(THINKING_LEVEL_LABELS) as ThinkingLevel[];

/** The default of pi (DEFAULT_THINKING_LEVEL), before the browser has a choice. */
export const DEFAULT_THINKING_LEVEL: ThinkingLevel = 'medium';

export function isThinkingLevel(value: unknown): value is ThinkingLevel {
  return THINKING_LEVELS.includes(value as ThinkingLevel);
}

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

export interface ThinkingSelect {
  items: SelectItem<ThinkingLevel>[];
  /** The level that the next message sends. */
  value: ThinkingLevel;
  /** Null for an enabled Select. */
  disabledReason: string | null;
}

/** The chosen level when the model has it. Else the next higher level of the model, else its highest level: the
 * clampThinkingLevel rule of pi, so the Select shows the level that pi uses. */
function chooseThinkingLevel(levels: readonly ThinkingLevel[], chosen: ThinkingLevel): ThinkingLevel {
  if (levels.includes(chosen)) {
    return chosen;
  }
  const higher = THINKING_LEVELS.slice(THINKING_LEVELS.indexOf(chosen)).find((level) => levels.includes(level));
  return higher ?? levels.at(-1) ?? 'off';
}

/** Only the thinking levels of the selected model. A model without reasoning has only "off", so the Select is disabled. */
export function describeThinkingSelect(
  providers: readonly Provider[],
  selection: ModelSelection,
  chosen: ThinkingLevel,
): ThinkingSelect {
  const model = providers
    .find((item) => item.id === selection.provider)
    ?.models.find((item) => item.id === selection.model);
  const levels = model?.thinking_levels ?? [];
  if (levels.every((level) => level === 'off')) {
    return { items: [], value: 'off', disabledReason: 'The model has no thinking levels.' };
  }
  return {
    items: levels.map((level) => ({ value: level, label: THINKING_LEVEL_LABELS[level] })),
    value: chooseThinkingLevel(levels, chosen),
    disabledReason: null,
  };
}

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

/** The socket of the open conversation. It does not connect again after a close (conversation_socket.ts). */
export type ConnectionState = 'connecting' | 'open' | 'closed';

export interface SendState {
  hasConversation: boolean;
  hasCredential: boolean;
  connection: ConnectionState;
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
      : state.connection === 'connecting'
        ? 'Connecting to the AI assistant.'
        : state.connection === 'closed'
          ? 'The connection to the AI assistant closed. Reload the page to send.'
          : null;
  return { action: 'send', label: 'Send', disabledReason };
}
