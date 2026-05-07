import { TerminalRoutePage } from '@/components/terminal/TerminalRoutePage';
import type { TerminalRouteSearchParams } from '@/lib/terminalRoutes';

type TerminalSymbolPageProps = {
  params: Promise<{ symbol: string }>;
  searchParams?: Promise<TerminalRouteSearchParams>;
};

export default async function AnalysisSymbolPage({ params, searchParams }: TerminalSymbolPageProps) {
  const [{ symbol }, resolvedSearchParams] = await Promise.all([
    params,
    searchParams ?? Promise.resolve({}),
  ]);

  return <TerminalRoutePage moduleId="ANALYSIS" searchParams={resolvedSearchParams} symbol={symbol} />;
}
