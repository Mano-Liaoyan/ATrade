// Unsaved edits of a strategy version stay only in the browser storage (docs/architecture/strategy.md section 9.1).
// A private window or blocked storage gives no draft. A full storage keeps no draft, also not the older one, so a
// reload cannot show older edits. Editing continues, and a write returns false.

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

function readStorage(storageKey: string): string | null {
  try {
    return localStorage.getItem(storageKey);
  } catch {
    return null;
  }
}

function clearStorage(storageKey: string): void {
  try {
    localStorage.removeItem(storageKey);
  } catch {
    // Blocked storage holds no draft.
  }
}

function writeStorage(storageKey: string, text: string): boolean {
  try {
    localStorage.setItem(storageKey, text);
    return true;
  } catch {
    clearStorage(storageKey);
    return false;
  }
}

export function readDraft(key: DraftKey): string | null {
  return readStorage(createStorageKey(key));
}

/** Returns false when the storage keeps no draft. */
export function writeDraft(key: DraftKey, code: string): boolean {
  return writeStorage(createStorageKey(key), code);
}

export function clearDraft(key: DraftKey): void {
  clearStorage(createStorageKey(key));
}

// Decided (#173): unsaved rules of the "Rules" tab stay in one draft for each strategy and rules version (versionNumber
// 0: the blank rules of a strategy without a version with rules).
function createRulesStorageKey(key: DraftKey): string {
  return `${RULES_DRAFT_KEY_PREFIX}.${String(key.strategyId)}.v${String(key.versionNumber)}`;
}

export function readRulesDraft(key: DraftKey): StrategyRules | null {
  const text = readStorage(createRulesStorageKey(key));
  if (text === null) {
    return null;
  }
  try {
    return JSON.parse(text) as StrategyRules;
  } catch {
    return null;
  }
}

/** Returns false when the storage keeps no draft. */
export function writeRulesDraft(key: DraftKey, rules: StrategyRules): boolean {
  return writeStorage(createRulesStorageKey(key), JSON.stringify(rules));
}

export function clearRulesDraft(key: DraftKey): void {
  clearStorage(createRulesStorageKey(key));
}

/** One version of one strategy, for example the open version that a start dialog selects. */
export interface StrategyVersionKey {
  strategyId: number;
  versionId: number;
}

export function formatVersionLabel(strategyName: string, versionNumber: number): string {
  return `${strategyName} v${String(versionNumber)}`;
}
