import type { InstrumentIdentityInput } from "./instrumentIdentity";
import { appendIdentityQueryParams, normalizeInstrumentIdentity } from "./instrumentIdentity";
import { SUPPORTED_CHART_RANGES, type ChartRange } from "@/types/marketData";
import type {
  DisabledTerminalModuleId,
  EnabledTerminalModuleId,
  TerminalModuleId,
} from "@/types/terminal";

export type TerminalRouteSearchParams = Record<string, string | string[] | undefined>;

export type TerminalSymbolModuleId = Extract<EnabledTerminalModuleId, "CHART" | "ANALYSIS" | "BACKTEST">;

export const TERMINAL_ENABLED_MODULE_ROUTES: Record<EnabledTerminalModuleId, string> = {
  HOME: "/",
  SEARCH: "/search",
  WATCHLIST: "/watchlist",
  CHART: "/chart",
  ANALYSIS: "/analysis",
  BACKTEST: "/backtest",
  STATUS: "/status",
  HELP: "/help",
};

export const TERMINAL_SYMBOL_MODULE_ROUTES: Record<TerminalSymbolModuleId, string> = {
  CHART: "/chart",
  ANALYSIS: "/analysis",
  BACKTEST: "/backtest",
};

export const TERMINAL_DISABLED_MODULE_ROUTES: Record<DisabledTerminalModuleId, string> = {
  NEWS: "/news",
  PORTFOLIO: "/portfolio",
  RESEARCH: "/research",
  SCREENER: "/screener",
  ECON: "/econ",
  AI: "/ai",
  NODE: "/node",
  ORDERS: "/orders",
};

export const TERMINAL_MODULE_ROUTES: Record<TerminalModuleId, string> = {
  ...TERMINAL_ENABLED_MODULE_ROUTES,
  ...TERMINAL_DISABLED_MODULE_ROUTES,
};

export type TerminalRouteAppState = {
  initialChartRange: ChartRange;
  initialDisabledModuleId: DisabledTerminalModuleId | null;
  initialIdentity: InstrumentIdentityInput | null;
  initialModuleId: EnabledTerminalModuleId;
  initialSymbol: string | null;
};

export function createTerminalRouteAppState({
  disabledModuleId = null,
  moduleId = "HOME",
  searchParams = {},
  symbol = null,
}: {
  disabledModuleId?: DisabledTerminalModuleId | null;
  moduleId?: EnabledTerminalModuleId;
  searchParams?: TerminalRouteSearchParams;
  symbol?: string | null;
}): TerminalRouteAppState {
  const initialSymbol = normalizeTerminalRouteSymbol(symbol);

  return {
    initialChartRange: createTerminalRouteChartRange(searchParams),
    initialDisabledModuleId: disabledModuleId,
    initialIdentity: initialSymbol ? createTerminalRouteIdentity(initialSymbol, searchParams) : null,
    initialModuleId: moduleId,
    initialSymbol,
  };
}

export function createTerminalRouteChartRange(searchParams: TerminalRouteSearchParams): ChartRange {
  const rangeQuery = firstTerminalQueryValue(searchParams.range)
    ?? firstTerminalQueryValue(searchParams.chartRange)
    ?? firstTerminalQueryValue(searchParams.timeframe);
  const normalizedRange = rangeQuery?.trim() as ChartRange | undefined;

  return normalizedRange && SUPPORTED_CHART_RANGES.includes(normalizedRange) ? normalizedRange : "1D";
}

export function createTerminalRouteIdentity(
  symbol: string,
  searchParams: TerminalRouteSearchParams,
): InstrumentIdentityInput | null {
  const provider = firstTerminalQueryValue(searchParams.provider);
  const providerSymbolId = firstTerminalQueryValue(searchParams.providerSymbolId);
  const exchange = firstTerminalQueryValue(searchParams.exchange);
  const currency = firstTerminalQueryValue(searchParams.currency);
  const assetClass = firstTerminalQueryValue(searchParams.assetClass);

  if (!provider && !providerSymbolId && !exchange && !currency && !assetClass) {
    return null;
  }

  return {
    symbol,
    provider,
    providerSymbolId,
    exchange,
    currency,
    assetClass,
  };
}

export function createTerminalModuleRoute(moduleId: TerminalModuleId): string {
  return TERMINAL_MODULE_ROUTES[moduleId];
}

export function createTerminalSymbolRoute(
  moduleId: TerminalSymbolModuleId,
  identity: InstrumentIdentityInput,
  options: { chartRange?: ChartRange | null } = {},
): string {
  const normalized = normalizeInstrumentIdentity(identity);
  const params = appendIdentityQueryParams(new URLSearchParams(), normalized);

  if (options.chartRange) {
    params.set("range", options.chartRange);
  }

  const query = params.toString();
  return `${TERMINAL_SYMBOL_MODULE_ROUTES[moduleId]}/${encodeURIComponent(normalized.symbol)}${query ? `?${query}` : ""}`;
}

export function isTerminalSymbolModuleId(moduleId: EnabledTerminalModuleId): moduleId is TerminalSymbolModuleId {
  return moduleId === "CHART" || moduleId === "ANALYSIS" || moduleId === "BACKTEST";
}

export function normalizeTerminalRouteSymbol(symbol: string | null | undefined): string | null {
  const trimmedSymbol = symbol?.trim();

  if (!trimmedSymbol) {
    return null;
  }

  try {
    return decodeURIComponent(trimmedSymbol).trim().toUpperCase();
  } catch {
    return trimmedSymbol.toUpperCase();
  }
}

export function firstTerminalQueryValue(value: string | string[] | undefined): string | null {
  if (Array.isArray(value)) {
    return value[0] ?? null;
  }

  return value ?? null;
}
