const WATCHLIST_STORAGE_KEY = 'atrade.paperTrading.watchlist.v1';

export function readWatchlist(): string[] {
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

export function writeWatchlist(symbols: string[]): string[] {
  const normalizedSymbols = normalizeSymbols(symbols);

  if (typeof window !== 'undefined') {
    window.localStorage.setItem(WATCHLIST_STORAGE_KEY, JSON.stringify(normalizedSymbols));
  }

  return normalizedSymbols;
}

export function toggleWatchlistSymbol(currentSymbols: string[], symbol: string): string[] {
  const normalizedSymbol = symbol.trim().toUpperCase();
  if (!normalizedSymbol) {
    return writeWatchlist(currentSymbols);
  }

  const normalizedCurrent = normalizeSymbols(currentSymbols);
  const nextSymbols = normalizedCurrent.includes(normalizedSymbol)
    ? normalizedCurrent.filter((candidate) => candidate !== normalizedSymbol)
    : [...normalizedCurrent, normalizedSymbol];

  return writeWatchlist(nextSymbols);
}

function normalizeSymbols(symbols: string[]): string[] {
  return Array.from(new Set(symbols.map((symbol) => symbol.trim().toUpperCase()).filter(Boolean))).sort();
}
