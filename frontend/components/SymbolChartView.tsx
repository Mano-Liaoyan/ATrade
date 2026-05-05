import { ATradeTerminalApp } from '@/components/terminal/ATradeTerminalApp';
import type { InstrumentIdentityInput } from '@/lib/instrumentIdentity';

type SymbolChartViewProps = {
  symbol: string;
  identity?: InstrumentIdentityInput | null;
};

export function SymbolChartView({ symbol, identity = null }: SymbolChartViewProps) {
  return <ATradeTerminalApp initialIdentity={identity} initialModuleId="CHART" initialSymbol={symbol} />;
}
