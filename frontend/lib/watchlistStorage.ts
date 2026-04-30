const WATCHLIST_STORAGE_KEY = 'atrade.paperTrading.watchlist.v1';
const WATCHLIST_BACKEND_MIGRATION_KEY = 'atrade.paperTrading.watchlist.backendMigrated.v1';
const SYMBOL_PATTERN = /^[A-Z0-9][A-Z0-9._-]{0,31}$/;

// Legacy browser storage is intentionally symbol-only. It is used only as a
// read-only fallback and one-time manual-symbol migration source; provider /
// market-specific pinned state always comes from the backend watchlist API.
export function readCachedWatchlist(): string[] {
  if (typeof window === 'undefined') {
    return [];
  }

  try {
    const rawValue = window.localStorage.getItem(WATCHLIST_STORAGE_KEY);
    if (!rawValue) {
      return [];
    }

    const parsed = JSON.parse(rawValue);
    if (!Array.isArray(parsed)) {
      return [];
    }

    return normalizeSymbols(parsed.filter((value): value is string => typeof value === 'string'));
  } catch {
    return [];
  }
}

export function writeCachedWatchlist(symbols: string[]): string[] {
  const normalizedSymbols = normalizeSymbols(symbols);

  if (typeof window !== 'undefined') {
    window.localStorage.setItem(WATCHLIST_STORAGE_KEY, JSON.stringify(normalizedSymbols));
  }

  return normalizedSymbols;
}

export function hasCompletedWatchlistMigration(): boolean {
  if (typeof window === 'undefined') {
    return false;
  }

  return window.localStorage.getItem(WATCHLIST_BACKEND_MIGRATION_KEY) === 'true';
}

export function markWatchlistMigrationCompleted(): void {
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(WATCHLIST_BACKEND_MIGRATION_KEY, 'true');
  }
}

function normalizeSymbols(symbols: string[]): string[] {
  return Array.from(
    new Set(
      symbols
        .map((symbol) => symbol.trim().toUpperCase())
        .filter((symbol) => SYMBOL_PATTERN.test(symbol)),
    ),
  ).sort();
}
