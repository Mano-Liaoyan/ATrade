import type { EnabledTerminalModuleId, TerminalLayoutPreferences, TerminalLayoutSizes } from "@/types/terminal";

export const TERMINAL_LAYOUT_STORAGE_KEY = "atrade.terminal.layout.v1";
export const TERMINAL_LAYOUT_VERSION = 1 as const;

export const DEFAULT_TERMINAL_LAYOUT_SIZES: TerminalLayoutSizes = {
  primary: 68,
  context: 32,
  monitor: 26,
};

export const DEFAULT_TERMINAL_LAYOUT_PREFERENCES: TerminalLayoutPreferences = {
  version: TERMINAL_LAYOUT_VERSION,
  activeModuleId: "HOME",
  railCollapsed: false,
  sizes: DEFAULT_TERMINAL_LAYOUT_SIZES,
};

const MIN_CONTEXT_PERCENT = 20;
const MAX_CONTEXT_PERCENT = 44;
const MIN_MONITOR_PERCENT = 16;
const MAX_MONITOR_PERCENT = 42;

export function readTerminalLayoutPreferences(storage: Storage | null = getTerminalLayoutStorage()): TerminalLayoutPreferences {
  if (!storage) {
    return DEFAULT_TERMINAL_LAYOUT_PREFERENCES;
  }

  try {
    const storedValue = storage.getItem(TERMINAL_LAYOUT_STORAGE_KEY);
    if (!storedValue) {
      return DEFAULT_TERMINAL_LAYOUT_PREFERENCES;
    }

    return sanitizeTerminalLayoutPreferences(JSON.parse(storedValue));
  } catch {
    return DEFAULT_TERMINAL_LAYOUT_PREFERENCES;
  }
}

export function writeTerminalLayoutPreferences(
  preferences: TerminalLayoutPreferences,
  storage: Storage | null = getTerminalLayoutStorage(),
): TerminalLayoutPreferences {
  const sanitized = sanitizeTerminalLayoutPreferences(preferences);

  if (!storage) {
    return sanitized;
  }

  try {
    storage.setItem(TERMINAL_LAYOUT_STORAGE_KEY, JSON.stringify(sanitized));
  } catch {
    return sanitized;
  }

  return sanitized;
}

export function resetTerminalLayoutPreferences(storage: Storage | null = getTerminalLayoutStorage()): TerminalLayoutPreferences {
  if (storage) {
    try {
      storage.removeItem(TERMINAL_LAYOUT_STORAGE_KEY);
    } catch {
      // Local storage can be unavailable in locked-down browser or desktop-wrapper contexts.
    }
  }

  return DEFAULT_TERMINAL_LAYOUT_PREFERENCES;
}

export function sanitizeTerminalLayoutPreferences(value: unknown): TerminalLayoutPreferences {
  if (!isTerminalLayoutPreferencesShape(value) || value.version !== TERMINAL_LAYOUT_VERSION) {
    return DEFAULT_TERMINAL_LAYOUT_PREFERENCES;
  }

  return {
    version: TERMINAL_LAYOUT_VERSION,
    activeModuleId: sanitizeActiveModuleId(value.activeModuleId),
    railCollapsed: value.railCollapsed === true,
    sizes: sanitizeTerminalLayoutSizes(value.sizes),
  };
}

export function sanitizeTerminalLayoutSizes(value: unknown): TerminalLayoutSizes {
  const candidate = isTerminalLayoutSizesShape(value) ? value : DEFAULT_TERMINAL_LAYOUT_SIZES;
  const context = clampNumber(candidate.context, MIN_CONTEXT_PERCENT, MAX_CONTEXT_PERCENT, DEFAULT_TERMINAL_LAYOUT_SIZES.context);
  const monitor = clampNumber(candidate.monitor, MIN_MONITOR_PERCENT, MAX_MONITOR_PERCENT, DEFAULT_TERMINAL_LAYOUT_SIZES.monitor);

  return {
    primary: 100 - context,
    context,
    monitor,
  };
}

export function createTerminalLayoutPreferences(next: Partial<TerminalLayoutPreferences>): TerminalLayoutPreferences {
  return sanitizeTerminalLayoutPreferences({
    ...DEFAULT_TERMINAL_LAYOUT_PREFERENCES,
    ...next,
    sizes: {
      ...DEFAULT_TERMINAL_LAYOUT_SIZES,
      ...next.sizes,
    },
  });
}

export function getTerminalLayoutStorage(): Storage | null {
  if (typeof window === "undefined" || !window.localStorage) {
    return null;
  }

  try {
    const probeKey = `${TERMINAL_LAYOUT_STORAGE_KEY}.probe`;
    window.localStorage.setItem(probeKey, "1");
    window.localStorage.removeItem(probeKey);
    return window.localStorage;
  } catch {
    return null;
  }
}

function sanitizeActiveModuleId(value: unknown): EnabledTerminalModuleId {
  if (
    value === "HOME" ||
    value === "SEARCH" ||
    value === "WATCHLIST" ||
    value === "CHART" ||
    value === "ANALYSIS" ||
    value === "STATUS" ||
    value === "HELP"
  ) {
    return value;
  }

  return DEFAULT_TERMINAL_LAYOUT_PREFERENCES.activeModuleId;
}

function isTerminalLayoutPreferencesShape(value: unknown): value is Partial<TerminalLayoutPreferences> & { sizes?: unknown } {
  return typeof value === "object" && value !== null;
}

function isTerminalLayoutSizesShape(value: unknown): value is Partial<TerminalLayoutSizes> {
  return typeof value === "object" && value !== null;
}

function clampNumber(value: unknown, min: number, max: number, fallback: number): number {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return fallback;
  }

  return Math.min(Math.max(value, min), max);
}
