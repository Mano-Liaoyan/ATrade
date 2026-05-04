import type { ChartRange, MarketDataSymbolIdentity, OhlcvCandle } from './marketData';

export type AnalysisEngineState = 'available' | 'not-configured' | 'unavailable' | string;

export type AnalysisResultStatus = 'completed' | 'not-configured' | 'failed' | string;

export type AnalysisEngineCapabilities = {
  supportsSignals: boolean;
  supportsBacktests: boolean;
  supportsMetrics: boolean;
  supportsOptimization: boolean;
  requiresExternalRuntime: boolean;
};

export type AnalysisEngineMetadata = {
  engineId: string;
  displayName: string;
  provider: string;
  version: string;
  state: AnalysisEngineState;
  message?: string | null;
};

export type AnalysisEngineDescriptor = {
  metadata: AnalysisEngineMetadata;
  capabilities: AnalysisEngineCapabilities;
};

export type AnalysisDataSource = {
  provider: string;
  source: string;
  generatedAtUtc: string;
};

export type AnalysisSignal = {
  time: string;
  kind: string;
  direction: string;
  confidence: number;
  rationale: string;
};

export type AnalysisMetric = {
  name: string;
  value: number;
  unit?: string | null;
};

export type BacktestSummary = {
  startUtc: string;
  endUtc: string;
  initialCapital: number;
  finalEquity: number;
  totalReturnPercent: number;
  tradeCount: number;
  winRatePercent: number;
};

export type AnalysisError = {
  code: string;
  message: string;
};

export type AnalysisResult = {
  status: AnalysisResultStatus;
  engine: AnalysisEngineMetadata;
  source: AnalysisDataSource;
  symbol: MarketDataSymbolIdentity;
  timeframe: ChartRange | string;
  generatedAtUtc: string;
  signals: AnalysisSignal[];
  metrics: AnalysisMetric[];
  backtest: BacktestSummary | null;
  error: AnalysisError | null;
};

export type RunAnalysisRequest = {
  symbol?: MarketDataSymbolIdentity | null;
  symbolCode?: string;
  timeframe: ChartRange;
  requestedAtUtc?: string;
  bars?: OhlcvCandle[];
  engineId?: string;
  strategyName?: string;
};
