// Unsaved edits of a strategy version stay only in the browser storage (docs/architecture/strategy.md section 1).

export interface DraftKey {
  strategyId: number;
  versionNumber: number;
}

const DRAFT_KEY_PREFIX = 'atrade.strategy-draft';

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

export function formatVersionLabel(strategyName: string, versionNumber: number): string {
  return `${strategyName} v${String(versionNumber)}`;
}
