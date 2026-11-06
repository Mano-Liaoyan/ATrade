// Unsaved edits stay in the browser storage, one draft for each strategy version, until the user saves.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vite-plus/test';
import {
  BLANK_RULES,
  clearDraft,
  clearRulesDraft,
  formatVersionLabel,
  readDraft,
  readRulesDraft,
  writeDraft,
  writeRulesDraft,
} from './index';

function createMemoryStorage(): Storage {
  const values = new Map<string, string>();
  return {
    get length() {
      return values.size;
    },
    clear: () => {
      values.clear();
    },
    getItem: (key) => values.get(key) ?? null,
    key: (index) => [...values.keys()][index] ?? null,
    removeItem: (key) => {
      values.delete(key);
    },
    setItem: (key, value) => {
      values.set(key, value);
    },
  };
}

function createBlockedStorage(): Storage {
  const storage = createMemoryStorage();
  const block = (): never => {
    throw new DOMException('The storage is not available.', 'SecurityError');
  };
  storage.getItem = block;
  storage.setItem = block;
  storage.removeItem = block;
  return storage;
}

beforeEach(() => {
  vi.stubGlobal('localStorage', createMemoryStorage());
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('strategy drafts', () => {
  it('returns the code that was written for the same strategy version', () => {
    writeDraft({ strategyId: 4, versionNumber: 2 }, 'x = 1\n');

    expect(readDraft({ strategyId: 4, versionNumber: 2 })).toBe('x = 1\n');
  });

  it('keeps the drafts of different versions apart', () => {
    writeDraft({ strategyId: 4, versionNumber: 2 }, 'x = 1\n');

    expect(readDraft({ strategyId: 4, versionNumber: 3 })).toBeNull();
    expect(readDraft({ strategyId: 5, versionNumber: 2 })).toBeNull();
  });

  it('forgets the draft after it is cleared', () => {
    writeDraft({ strategyId: 4, versionNumber: 2 }, 'x = 1\n');

    clearDraft({ strategyId: 4, versionNumber: 2 });

    expect(readDraft({ strategyId: 4, versionNumber: 2 })).toBeNull();
  });
});

describe('strategy drafts without browser storage', () => {
  const key = { strategyId: 4, versionNumber: 2 };

  it('gives no draft and throws no error when the storage is blocked', () => {
    vi.stubGlobal('localStorage', createBlockedStorage());

    expect(readDraft(key)).toBeNull();
    expect(readRulesDraft(key)).toBeNull();
    expect(() => {
      writeDraft(key, 'x = 1\n');
      writeRulesDraft(key, BLANK_RULES);
      clearDraft(key);
      clearRulesDraft(key);
    }).not.toThrow();
  });

  it('throws no error when a write exceeds the quota', () => {
    vi.spyOn(localStorage, 'setItem').mockImplementation(() => {
      throw new DOMException('The quota is exceeded.', 'QuotaExceededError');
    });

    expect(() => {
      writeDraft(key, 'x = 1\n');
      writeRulesDraft(key, BLANK_RULES);
    }).not.toThrow();
  });
});

describe('formatVersionLabel', () => {
  it('shows the strategy name and the version number', () => {
    expect(formatVersionLabel('Moving average', 3)).toBe('Moving average v3');
  });
});

describe('rules drafts', () => {
  it('keeps unsaved rules for one strategy and rules version until they are cleared', () => {
    const key = { strategyId: 4, versionNumber: 2 };

    writeRulesDraft(key, BLANK_RULES);

    expect(readRulesDraft(key)).toEqual(BLANK_RULES);
    expect(readRulesDraft({ strategyId: 4, versionNumber: 3 })).toBeNull();
    clearRulesDraft(key);
    expect(readRulesDraft(key)).toBeNull();
  });
});
