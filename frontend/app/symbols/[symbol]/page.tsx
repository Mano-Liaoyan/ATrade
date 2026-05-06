import { ATradeTerminalApp } from '@/components/terminal/ATradeTerminalApp';
import { SUPPORTED_CHART_RANGES, type ChartRange } from '@/types/marketData';
import type { EnabledTerminalModuleId } from '@/types/terminal';

type SymbolPageProps = {
  params: Promise<{
    symbol: string;
  }>;
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

export default async function SymbolPage({ params, searchParams }: SymbolPageProps) {
  const { symbol } = await params;
  const resolvedSearchParams = searchParams ? await searchParams : {};
  const normalizedSymbol = decodeURIComponent(symbol).toUpperCase();
  const identity = createQueryIdentity(normalizedSymbol, resolvedSearchParams);
  const initialModuleId = createInitialModuleId(firstQueryValue(resolvedSearchParams.module));
  const initialChartRange = createInitialChartRange(
    firstQueryValue(resolvedSearchParams.range)
      ?? firstQueryValue(resolvedSearchParams.chartRange)
      ?? firstQueryValue(resolvedSearchParams.timeframe),
  );

  return <ATradeTerminalApp initialChartRange={initialChartRange} initialIdentity={identity} initialModuleId={initialModuleId} initialSymbol={normalizedSymbol} />;
}

function createInitialModuleId(moduleQuery: string | null): EnabledTerminalModuleId {
  const normalizedModule = moduleQuery?.trim().toUpperCase();

  if (normalizedModule === 'ANALYSIS' || normalizedModule === 'BACKTEST' || normalizedModule === 'STATUS' || normalizedModule === 'HELP') {
    return normalizedModule;
  }

  return 'CHART';
}

function createInitialChartRange(rangeQuery: string | null): ChartRange {
  const normalizedRange = rangeQuery?.trim() as ChartRange | undefined;

  return normalizedRange && SUPPORTED_CHART_RANGES.includes(normalizedRange) ? normalizedRange : '1D';
}

function createQueryIdentity(symbol: string, searchParams: Record<string, string | string[] | undefined>) {
  const provider = firstQueryValue(searchParams.provider);
  const providerSymbolId = firstQueryValue(searchParams.providerSymbolId);
  const exchange = firstQueryValue(searchParams.exchange);
  const currency = firstQueryValue(searchParams.currency);
  const assetClass = firstQueryValue(searchParams.assetClass);

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

function firstQueryValue(value: string | string[] | undefined): string | null {
  if (Array.isArray(value)) {
    return value[0] ?? null;
  }

  return value ?? null;
}
