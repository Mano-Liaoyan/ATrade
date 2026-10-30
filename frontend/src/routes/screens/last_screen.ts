// /screens opens the screen that the user opened last (docs/architecture/screen.md section 24.13). The id is in the
// browser storage: the choice belongs to this browser. Private windows and blocked storage give no id.
const LAST_SCREEN_KEY = 'atrade.screen-page.last-screen';

export function readLastScreenId(): number | null {
  try {
    const stored = window.localStorage.getItem(LAST_SCREEN_KEY);
    return stored === null ? null : Number(stored);
  } catch {
    return null;
  }
}

export function writeLastScreenId(screenId: number): void {
  try {
    window.localStorage.setItem(LAST_SCREEN_KEY, String(screenId));
  } catch {
    // Without storage, /screens opens the first screen.
  }
}
