// The theme choice of the header theme button: the click order, and the read and save in browser storage.
import { describe, expect, it } from 'vite-plus/test';
import { nextThemeChoice, readThemeChoice, saveThemeChoice, THEME_STORAGE_KEY } from './theme_choice';

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

function storageNotAvailable(): Storage {
  throw new DOMException('The storage is not available.', 'SecurityError');
}

describe('nextThemeChoice', () => {
  it('goes from System to Light to Dark and back to System', () => {
    expect(nextThemeChoice('system')).toBe('light');
    expect(nextThemeChoice('light')).toBe('dark');
    expect(nextThemeChoice('dark')).toBe('system');
  });
});

describe('readThemeChoice', () => {
  it('reads the saved choice', () => {
    const storage = createMemoryStorage();
    storage.setItem(THEME_STORAGE_KEY, 'dark');

    expect(readThemeChoice(() => storage)).toBe('dark');
  });

  it('gives System when nothing is saved', () => {
    expect(readThemeChoice(() => createMemoryStorage())).toBe('system');
  });

  it('gives System for a saved value that is not a theme choice', () => {
    const storage = createMemoryStorage();
    storage.setItem(THEME_STORAGE_KEY, 'purple');

    expect(readThemeChoice(() => storage)).toBe('system');
  });

  it('gives System when the storage is not available', () => {
    expect(readThemeChoice(storageNotAvailable)).toBe('system');
  });
});

describe('saveThemeChoice', () => {
  it('saves a choice that the next read gives back', () => {
    const storage = createMemoryStorage();

    saveThemeChoice('light', () => storage);

    expect(readThemeChoice(() => storage)).toBe('light');
  });

  it('removes the saved value for System', () => {
    const storage = createMemoryStorage();
    storage.setItem(THEME_STORAGE_KEY, 'dark');

    saveThemeChoice('system', () => storage);

    expect(storage.getItem(THEME_STORAGE_KEY)).toBeNull();
  });

  it('does not fail when the storage is not available', () => {
    expect(() => {
      saveThemeChoice('dark', storageNotAvailable);
    }).not.toThrow();
  });

  it('does not fail when the storage refuses the value', () => {
    const fullStorage = createMemoryStorage();
    fullStorage.setItem = () => {
      throw new DOMException('The quota is exceeded.', 'QuotaExceededError');
    };

    expect(() => {
      saveThemeChoice('dark', () => fullStorage);
    }).not.toThrow();
  });
});
