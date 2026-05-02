import Link from 'next/link';
import { SymbolChartView } from '../../../components/SymbolChartView';

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

  return (
    <main className="workspace-shell">
      <Link className="back-link" href="/">
        ← Back to trading workspace
      </Link>

      <SymbolChartView symbol={normalizedSymbol} identity={identity} />
    </main>
  );
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
