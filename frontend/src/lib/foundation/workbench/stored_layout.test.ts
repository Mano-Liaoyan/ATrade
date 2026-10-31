// The browser keeps the layout of each workbench part in localStorage. Blocked storage does not stop the page.
import { afterEach, describe, expect, it, vi } from 'vite-plus/test';
import { readStoredLayout, writeStoredLayout } from './index';

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
    key: () => null,
    removeItem: (key) => {
      values.delete(key);
    },
    setItem: (key, value) => {
      values.set(key, value);
    },
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('readStoredLayout and writeStoredLayout', () => {
  it('reads the value that was written', () => {
    vi.stubGlobal('localStorage', createMemoryStorage());

    writeStoredLayout('atrade.test', { isMinimized: true });

    expect(readStoredLayout('atrade.test')).toEqual({ isMinimized: true });
  });

  it('reads null for a missing key and for damaged JSON', () => {
    const storage = createMemoryStorage();
    storage.setItem('atrade.damaged', '{');
    vi.stubGlobal('localStorage', storage);

    expect(readStoredLayout('atrade.missing')).toBeNull();
    expect(readStoredLayout('atrade.damaged')).toBeNull();
  });

  it('reads null and writes nothing when the storage is blocked', () => {
    vi.stubGlobal('localStorage', {
      getItem: () => {
        throw new Error('blocked');
      },
      setItem: () => {
        throw new Error('blocked');
      },
    });

    expect(readStoredLayout('atrade.test')).toBeNull();
    expect(() => {
      writeStoredLayout('atrade.test', { isMinimized: true });
    }).not.toThrow();
  });
});
