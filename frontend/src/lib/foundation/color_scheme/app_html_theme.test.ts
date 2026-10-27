// src/app.html has a copy of the theme read in an inline script, so the saved theme applies before the first paint.
// This test runs that script on each choice that saveThemeChoice saves, so the copy cannot drift from theme_choice.ts.
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vite-plus/test';
import { saveThemeChoice, THEME_STORAGE_KEY, type ThemeChoice } from './theme_choice';

const APP_HTML = readFileSync(new URL('../../../app.html', import.meta.url), 'utf8');

function readInlineScript(): string {
  const match = /<script>([\s\S]*?)<\/script>/.exec(APP_HTML);
  if (match?.[1] === undefined) {
    throw new Error('src/app.html has no inline theme script.');
  }
  return match[1];
}

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

// Runs the inline script with the storage and returns the data-theme attribute that it puts on <html>.
function runInlineScript(storage: Storage): string | null {
  const attributes = new Map<string, string>();
  const fakeWindow = { localStorage: storage };
  const fakeDocument = {
    documentElement: {
      setAttribute: (name: string, value: string) => {
        attributes.set(name, value);
      },
    },
  };
  // eslint-disable-next-line @typescript-eslint/no-implied-eval -- the test runs the script text of src/app.html.
  const script = new Function('window', 'document', readInlineScript()) as (window: unknown, document: unknown) => void;
  script(fakeWindow, fakeDocument);
  return attributes.get('data-theme') ?? null;
}

describe('the inline theme script of src/app.html', () => {
  const cases: { choice: ThemeChoice; theme: string | null }[] = [
    { choice: 'light', theme: 'light' },
    { choice: 'dark', theme: 'dark' },
    { choice: 'system', theme: null },
  ];
  for (const { choice, theme } of cases) {
    it(`applies the saved ${choice} choice`, () => {
      const storage = createMemoryStorage();
      saveThemeChoice(choice, () => storage);
      expect(runInlineScript(storage)).toBe(theme);
    });
  }

  it('ignores a value that is not a theme choice', () => {
    const storage = createMemoryStorage();
    storage.setItem(THEME_STORAGE_KEY, 'sepia');
    expect(runInlineScript(storage)).toBeNull();
  });
});
