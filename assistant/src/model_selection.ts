// The provider, model, and credential that the user selects for a conversation (docs/architecture/assistant.md 25.7.1).
import type { ModelRuntime } from '@earendil-works/pi-coding-agent';

/** The thinking levels of pi, in its order (THINKING_LEVEL_OPTIONS of pi-coding-agent). */
export const THINKING_LEVELS = ['off', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max'] as const;
export type ThinkingLevel = (typeof THINKING_LEVELS)[number];

export function isThinkingLevel(value: unknown): value is ThinkingLevel {
  return THINKING_LEVELS.includes(value as ThinkingLevel);
}

/** The model fields that give its thinking levels (Model of pi-ai). */
export interface ThinkingModel {
  reasoning?: boolean;
  thinkingLevelMap?: Partial<Record<ThinkingLevel, string | null>>;
}

/** The thinking levels of a model, by the rule of getSupportedThinkingLevels of pi-ai (pi-coding-agent does not export
 * it): only "off" without reasoning; a level that the map sets to null is not supported; "xhigh" and "max" only when the
 * map names them. */
export function listThinkingLevels(model: ThinkingModel): ThinkingLevel[] {
  if (model.reasoning !== true) {
    return ['off'];
  }
  return THINKING_LEVELS.filter((level) => {
    const mapped = model.thinkingLevelMap?.[level];
    if (mapped === null) {
      return false;
    }
    return level === 'xhigh' || level === 'max' ? mapped !== undefined : true;
  });
}

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
