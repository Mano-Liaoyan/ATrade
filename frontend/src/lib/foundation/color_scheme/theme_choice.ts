// The theme choice and the color scheme watch. The public entry is index.ts.

const DARK_SCHEME_QUERY = '(prefers-color-scheme: dark)';
const THEME_ATTRIBUTE = 'data-theme';

/** The localStorage key of the theme choice. src/app.html reads the same key before the first paint. */
export const THEME_STORAGE_KEY = 'atrade.theme';

/** System follows prefers-color-scheme. Light is Carbon g10 and Dark is Carbon g100 for all system settings. */
export type ThemeChoice = 'system' | 'light' | 'dark';

const THEME_CHOICES: readonly ThemeChoice[] = ['system', 'light', 'dark'];

function isThemeChoice(value: string | null): value is ThemeChoice {
  return THEME_CHOICES.some((choice) => choice === value);
}

function openLocalStorage(): Storage {
  return window.localStorage;
}

/** The choice after a click of the theme button: System, then Light, then Dark, then System again. */
export function nextThemeChoice(choice: ThemeChoice): ThemeChoice {
  return THEME_CHOICES[(THEME_CHOICES.indexOf(choice) + 1) % THEME_CHOICES.length] ?? 'system';
}

/** The saved theme choice. It is System when nothing valid is saved or when the storage is not available. */
export function readThemeChoice(openStorage: () => Storage = openLocalStorage): ThemeChoice {
  try {
    const saved = openStorage().getItem(THEME_STORAGE_KEY);
    return isThemeChoice(saved) ? saved : 'system';
  } catch {
    return 'system';
  }
}

/** Saves the theme choice. When the storage is not available, the choice applies only until the page reloads. */
export function saveThemeChoice(choice: ThemeChoice, openStorage: () => Storage = openLocalStorage): void {
  try {
    if (choice === 'system') {
      openStorage().removeItem(THEME_STORAGE_KEY);
    } else {
      openStorage().setItem(THEME_STORAGE_KEY, choice);
    }
  } catch {
    // The page works without the storage.
  }
}

/** Puts the theme choice on <html>: data-theme="light" or "dark", and no attribute for System. */
export function applyThemeChoice(choice: ThemeChoice): void {
  const root = document.documentElement;
  if (choice === 'system') {
    root.removeAttribute(THEME_ATTRIBUTE);
  } else {
    root.setAttribute(THEME_ATTRIBUTE, choice);
  }
}

/** True when the page shows the dark tokens now: the Dark choice, or the System choice with a dark system. */
export function isDarkColorScheme(): boolean {
  const theme = document.documentElement.getAttribute(THEME_ATTRIBUTE);
  if (theme === 'light' || theme === 'dark') {
    return theme === 'dark';
  }
  return typeof window.matchMedia === 'function' && window.matchMedia(DARK_SCHEME_QUERY).matches;
}

/**
 * Calls `onChange` after each change of the color tokens: a change of prefers-color-scheme or of the data-theme
 * attribute on <html>. Returns the function that ends the watch.
 */
export function watchColorScheme(onChange: () => void): () => void {
  const darkSchemeQuery = typeof window.matchMedia === 'function' ? window.matchMedia(DARK_SCHEME_QUERY) : null;
  darkSchemeQuery?.addEventListener('change', onChange);
  const themeObserver = new MutationObserver(onChange);
  themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: [THEME_ATTRIBUTE] });
  return () => {
    darkSchemeQuery?.removeEventListener('change', onChange);
    themeObserver.disconnect();
  };
}
