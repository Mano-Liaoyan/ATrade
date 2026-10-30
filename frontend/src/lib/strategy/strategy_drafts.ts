// Unsaved edits of a strategy version stay only in the browser storage (docs/architecture/strategy.md section 9.1).

import type { StrategyRules } from './strategy_rules';

export interface DraftKey {
  strategyId: number;
  versionNumber: number;
}

const DRAFT_KEY_PREFIX = 'atrade.strategy-draft';
const RULES_DRAFT_KEY_PREFIX = 'atrade.strategy-rules-draft';

function createStorageKey(key: DraftKey): string {
  return `${DRAFT_KEY_PREFIX}.${String(key.strategyId)}.v${String(key.versionNumber)}`;
}

export function readDraft(storage: Storage, key: DraftKey): string | null {
  return storage.getItem(createStorageKey(key));
}

export function writeDraft(storage: Storage, key: DraftKey, code: string): void {
  storage.setItem(createStorageKey(key), code);
}

export function clearDraft(storage: Storage, key: DraftKey): void {
  storage.removeItem(createStorageKey(key));
}

// Decided (#173): unsaved rules of the "Rules" tab stay in one draft for each strategy and rules version (versionNumber
// 0: the blank rules of a strategy without a version with rules).
function createRulesStorageKey(key: DraftKey): string {
  return `${RULES_DRAFT_KEY_PREFIX}.${String(key.strategyId)}.v${String(key.versionNumber)}`;
}

export function readRulesDraft(storage: Storage, key: DraftKey): StrategyRules | null {
  const text = storage.getItem(createRulesStorageKey(key));
  if (text === null) {
    return null;
  }
  try {
    return JSON.parse(text) as StrategyRules;
  } catch {
    return null;
  }
}

export function writeRulesDraft(storage: Storage, key: DraftKey, rules: StrategyRules): void {
  storage.setItem(createRulesStorageKey(key), JSON.stringify(rules));
}

export function clearRulesDraft(storage: Storage, key: DraftKey): void {
  storage.removeItem(createRulesStorageKey(key));
}

/** One version of one strategy, for example the open version that a start dialog selects. */
export interface StrategyVersionKey {
  strategyId: number;
  versionId: number;
}

export function formatVersionLabel(strategyName: string, versionNumber: number): string {
  return `${strategyName} v${String(versionNumber)}`;
}
