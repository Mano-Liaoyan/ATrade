import Link from 'next/link';
import { SymbolChartView } from '../../../components/SymbolChartView';

type SymbolPageProps = {
  params: Promise<{
    symbol: string;
  }>;
};

export default async function SymbolPage({ params }: SymbolPageProps) {
  const { symbol } = await params;
  const normalizedSymbol = decodeURIComponent(symbol).toUpperCase();

  return (
    <main className="workspace-shell">
      <Link className="back-link" href="/">
        ← Back to trading workspace
      </Link>

      <SymbolChartView symbol={normalizedSymbol} />
    </main>
  );
}
