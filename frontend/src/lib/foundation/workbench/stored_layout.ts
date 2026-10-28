// The browser keeps the layout of each workbench part (panel sizes, collapsed side columns) in localStorage.
// A private window or blocked storage gives null, and the page works with the default layout until it reloads.

export function readStoredLayout(key: string): unknown {
  try {
    const text = localStorage.getItem(key);
    return text === null ? null : (JSON.parse(text) as unknown);
  } catch {
    return null;
  }
}

export function writeStoredLayout(key: string, layout: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(layout));
  } catch {
    // Blocked storage: the layout stays only until the page reloads.
  }
}
