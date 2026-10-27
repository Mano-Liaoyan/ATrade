// Unsaved edits stay in the browser storage, one draft for each strategy version, until the user saves.
import { describe, expect, it } from 'vitest';
import { clearDraft, formatVersionLabel, readDraft, writeDraft } from './index';

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

describe('strategy drafts', () => {
  it('returns the code that was written for the same strategy version', () => {
    const storage = createMemoryStorage();

    writeDraft(storage, { strategyId: 4, versionNumber: 2 }, 'x = 1\n');

    expect(readDraft(storage, { strategyId: 4, versionNumber: 2 })).toBe('x = 1\n');
  });

  it('keeps the drafts of different versions apart', () => {
    const storage = createMemoryStorage();

    writeDraft(storage, { strategyId: 4, versionNumber: 2 }, 'x = 1\n');

    expect(readDraft(storage, { strategyId: 4, versionNumber: 3 })).toBeNull();
    expect(readDraft(storage, { strategyId: 5, versionNumber: 2 })).toBeNull();
  });

  it('forgets the draft after it is cleared', () => {
    const storage = createMemoryStorage();
    writeDraft(storage, { strategyId: 4, versionNumber: 2 }, 'x = 1\n');

    clearDraft(storage, { strategyId: 4, versionNumber: 2 });

    expect(readDraft(storage, { strategyId: 4, versionNumber: 2 })).toBeNull();
  });
});

describe('formatVersionLabel', () => {
  it('shows the strategy name and the version number', () => {
    expect(formatVersionLabel('Moving average', 3)).toBe('Moving average v3');
  });
});
