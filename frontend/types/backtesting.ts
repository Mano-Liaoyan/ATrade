import type { ChartRange, MarketDataSymbolIdentity } from './marketData';

export type PaperCapitalSource = 'ibkr-paper-balance' | 'local-paper-ledger' | 'unavailable' | string;

export type PaperCapitalAvailabilityState =
  | 'available'
  | 'disabled'
  | 'credentials-missing'
  | 'unauthenticated'
  | 'rejected-live'
  | 'timeout'
  | 'provider-unavailable'
  | 'error'
  | 'unconfigured'
  | string;

export type PaperCapitalMessageSeverity = 'info' | 'warning' | 'error' | string;

export type PaperCapitalMessage = {
  code: string;
  message: string;
  severity: PaperCapitalMessageSeverity;
};

export type IbkrPaperCapitalAvailability = {
  available: boolean;
  state: PaperCapitalAvailabilityState;
  capital: number | null;
  currency: string;
  messages: PaperCapitalMessage[];
};

export type PaperCapitalResponse = {
  effectiveCapital: number | null;
  currency: string;
  source: PaperCapitalSource;
  ibkrAvailable: IbkrPaperCapitalAvailability;
  localConfigured: boolean;
  localCapital: number | null;
  messages: PaperCapitalMessage[];
};

export type LocalPaperCapitalUpdateRequest = {
  amount: number | null;
  currency?: string | null;
};

export type BacktestRunStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | string;

export type BacktestStrategyId = 'sma-crossover' | 'rsi-mean-reversion' | 'breakout';

export type BacktestStrategyParameterType = 'integer' | 'decimal';

export type BacktestStrategyParameterDefinition = {
  name: string;
  displayName: string;
  description: string;
  valueType: BacktestStrategyParameterType;
  defaultValue: number;
  minimumValue: number;
  maximumValue: number;
};

export type BacktestStrategyDefinition = {
  id: BacktestStrategyId;
  displayName: string;
  description: string;
  parameters: readonly BacktestStrategyParameterDefinition[];
};

export const BACKTEST_STRATEGY_DEFINITIONS: readonly BacktestStrategyDefinition[] = [
  {
    id: 'sma-crossover',
    displayName: 'SMA crossover',
    description: 'Generates long/flat signals when a short simple moving average crosses a longer simple moving average.',
    parameters: [
      {
        name: 'shortWindow',
        displayName: 'Short SMA window',
        description: 'Number of bars used for the faster moving average.',
        valueType: 'integer',
        defaultValue: 20,
        minimumValue: 2,
        maximumValue: 250,
      },
      {
        name: 'longWindow',
        displayName: 'Long SMA window',
        description: 'Number of bars used for the slower moving average; must be greater than the short window.',
        valueType: 'integer',
        defaultValue: 50,
        minimumValue: 3,
        maximumValue: 500,
      },
    ],
  },
  {
    id: 'rsi-mean-reversion',
    displayName: 'RSI mean reversion',
    description: 'Generates oversold/overbought reversal signals from a relative strength index threshold model.',
    parameters: [
      {
        name: 'rsiPeriod',
        displayName: 'RSI period',
        description: 'Number of bars used to calculate RSI.',
        valueType: 'integer',
        defaultValue: 14,
        minimumValue: 2,
        maximumValue: 100,
      },
      {
        name: 'oversoldThreshold',
        displayName: 'Oversold threshold',
        description: 'RSI value at or below which the strategy may enter a long position.',
        valueType: 'decimal',
        defaultValue: 30,
        minimumValue: 1,
        maximumValue: 99,
      },
      {
        name: 'overboughtThreshold',
        displayName: 'Overbought threshold',
        description: 'RSI value at or above which the strategy may exit a long position.',
        valueType: 'decimal',
        defaultValue: 70,
        minimumValue: 1,
        maximumValue: 99,
      },
    ],
  },
  {
    id: 'breakout',
    displayName: 'Breakout',
    description: 'Generates long/flat signals when price closes above or below the prior lookback window.',
    parameters: [
      {
        name: 'lookbackWindow',
        displayName: 'Lookback window',
        description: 'Number of prior bars used to calculate breakout and breakdown levels.',
        valueType: 'integer',
        defaultValue: 20,
        minimumValue: 2,
        maximumValue: 250,
      },
    ],
  },
] as const satisfies readonly BacktestStrategyDefinition[];

export type BacktestBenchmarkMode = 'none' | 'buy-and-hold';

export type BacktestCostModel = {
  commissionPerTrade?: number | null;
  commissionBps?: number | null;
  currency?: string | null;
};

export type BacktestCostModelSnapshot = {
  commissionPerTrade: number;
  commissionBps: number;
  currency: string;
};

export type BacktestCreateRequest = {
  symbol?: MarketDataSymbolIdentity | null;
  symbolCode?: string;
  strategyId: BacktestStrategyId;
  parameters?: Record<string, number>;
  chartRange: ChartRange;
  costModel?: BacktestCostModel | null;
  slippageBps?: number | null;
  benchmarkMode?: BacktestBenchmarkMode;
  engineId?: string | null;
};

export type BacktestRequestSnapshot = {
  symbol: MarketDataSymbolIdentity;
  strategyId: BacktestStrategyId | string;
  parameters: Record<string, unknown>;
  chartRange: ChartRange | string;
  costModel: BacktestCostModelSnapshot;
  slippageBps: number;
  benchmarkMode: BacktestBenchmarkMode | string;
  engineId?: string | null;
};

export type BacktestCapitalSnapshot = {
  initialCapital: number;
  currency: string;
  capitalSource: PaperCapitalSource;
};

export type BacktestError = {
  code: string;
  message: string;
};

export type BacktestResultEngineEnvelope = {
  engineId: string;
  displayName: string;
  provider: string;
  version: string;
  state: string;
  message?: string | null;
};

export type BacktestResultSymbolEnvelope = {
  symbol: string;
  provider: string;
  providerSymbolId: string | null;
  assetClass: string;
  exchange: string;
  currency: string;
};

export type BacktestResultSourceEnvelope = {
  provider: string;
  marketDataSource: string;
  generatedAtUtc: string;
};

export type BacktestResultSignalEnvelope = {
  time: string;
  kind: string;
  direction: string;
  confidence: number;
  rationale: string;
};

export type BacktestResultMetricEnvelope = {
  name: string;
  value: number;
  unit?: string | null;
};

export type BacktestResultSummaryEnvelope = {
  startUtc: string;
  endUtc: string;
  initialCapital: number;
  finalEquity: number;
  totalReturnPercent: number;
  tradeCount: number;
  winRatePercent: number;
  maxDrawdownPercent: number;
  totalCost: number;
};

export type BacktestResultEquityCurvePointEnvelope = {
  time: string;
  equity: number;
  drawdownPercent: number;
};

export type BacktestResultTradeEnvelope = {
  entryTime: string;
  exitTime?: string | null;
  direction: string;
  entryPrice: number;
  exitPrice?: number | null;
  quantity: number;
  grossPnl: number;
  netPnl: number;
  returnPercent: number;
  totalCost: number;
  exitReason: string;
};

export type BacktestResultBenchmarkEnvelope = {
  mode: string;
  label: string;
  initialCapital: number;
  finalEquity: number;
  totalReturnPercent: number;
  equityCurve: BacktestResultEquityCurvePointEnvelope[];
};

export type BacktestResultAccountingEnvelope = {
  commissionPerTrade: number;
  commissionBps: number;
  slippageBps: number;
  currency: string;
};

export type BacktestCompletedResultEnvelope = {
  schemaVersion: string;
  status: string;
  strategyId: BacktestStrategyId | string;
  parameters: Record<string, unknown>;
  engine: BacktestResultEngineEnvelope;
  symbol: BacktestResultSymbolEnvelope;
  chartRange: ChartRange | string;
  generatedAtUtc: string;
  source: BacktestResultSourceEnvelope;
  signals: BacktestResultSignalEnvelope[];
  metrics: BacktestResultMetricEnvelope[];
  backtest: BacktestResultSummaryEnvelope | null;
  equityCurve: BacktestResultEquityCurvePointEnvelope[];
  trades: BacktestResultTradeEnvelope[];
  benchmark: BacktestResultBenchmarkEnvelope | null;
  accounting: BacktestResultAccountingEnvelope;
};

export type BacktestRunEnvelope = {
  id: string;
  status: BacktestRunStatus;
  sourceRunId?: string | null;
  request: BacktestRequestSnapshot;
  capital: BacktestCapitalSnapshot;
  createdAtUtc: string;
  updatedAtUtc: string;
  startedAtUtc?: string | null;
  completedAtUtc?: string | null;
  error?: BacktestError | null;
  result?: BacktestCompletedResultEnvelope | null;
};

export type BacktestRunUpdateSymbolPayload = {
  symbol: string;
  provider: string;
  providerSymbolId: string | null;
  assetClass: string;
  exchange: string;
  currency: string;
};

export type BacktestRunUpdatePayload = {
  event: string;
  id: string;
  status: BacktestRunStatus;
  sourceRunId?: string | null;
  symbol: BacktestRunUpdateSymbolPayload;
  strategyId: BacktestStrategyId | string;
  engineId?: string | null;
  chartRange: ChartRange | string;
  createdAtUtc: string;
  updatedAtUtc: string;
  startedAtUtc?: string | null;
  completedAtUtc?: string | null;
  error?: BacktestError | null;
  result?: BacktestCompletedResultEnvelope | null;
};

export const BACKTEST_RUN_UPDATE_EVENTS = [
  'backtestRunCreated',
  'backtestRunStatusChanged',
  'backtestRunCompleted',
  'backtestRunFailed',
  'backtestRunCancelled',
] as const;

export type BacktestRunUpdateEvent = (typeof BACKTEST_RUN_UPDATE_EVENTS)[number];
