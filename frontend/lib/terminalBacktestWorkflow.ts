'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import {
  BacktestClientError,
  cancelBacktestRun,
  connectBacktestRunStream,
  createBacktestRun,
  getBacktestRun,
  getPaperCapital,
  listBacktestRuns,
  retryBacktestRun,
  updateLocalPaperCapital,
  type BacktestStreamState,
} from './backtestClient';
import { normalizeInstrumentIdentity, type InstrumentIdentityInput, type NormalizedInstrumentIdentity } from './instrumentIdentity';
import {
  BACKTEST_STRATEGY_DEFINITIONS,
  type BacktestBenchmarkMode,
  type BacktestCreateRequest,
  type BacktestResultEquityCurvePointEnvelope,
  type BacktestRunEnvelope,
  type BacktestRunStatus,
  type BacktestRunUpdatePayload,
  type BacktestStrategyDefinition,
  type BacktestStrategyId,
  type PaperCapitalResponse,
} from '../types/backtesting';
import { CHART_RANGE_DESCRIPTIONS, CHART_RANGE_LABELS, type ChartRange, type MarketDataSymbolIdentity } from '../types/marketData';

export const TERMINAL_BACKTEST_NO_ORDER_COPY = 'Backtests are simulation-only: no order tickets, buy/sell buttons, broker routing, previews, or live-trading controls are available.';
export const TERMINAL_BACKTEST_SIGNALR_COPY = 'Status updates stream from ATrade.Api /hubs/backtests; HTTP is used for initial load and reconnect recovery without polling or fake results.';
export const TERMINAL_BACKTEST_CAPITAL_COPY = 'Backtest creation uses the effective paper-capital source from ATrade.Api and blocks runs when capital is unavailable.';
export const TERMINAL_BACKTEST_COMPARISON_COPY = 'Comparison uses only completed saved runs with persisted result/equity curves from /api/backtests; queued, running, failed, and cancelled runs stay visible but are not selectable.';

const BACKTEST_COMPARISON_STRATEGY_COLORS = ['#f59e0b', '#22c55e', '#60a5fa', '#f97316', '#a78bfa', '#14b8a6', '#f43f5e', '#eab308'] as const;
const BACKTEST_COMPARISON_BENCHMARK_COLORS = ['#fcd34d', '#86efac', '#93c5fd', '#fdba74', '#c4b5fd', '#5eead4', '#fda4af', '#fde047'] as const;

export type TerminalBacktestWorkflowOptions = {
  initialChartRange?: ChartRange;
  initialIdentity?: InstrumentIdentityInput | null;
  initialSymbol?: string | null;
  historyLimit?: number;
};

export type TerminalBacktestFieldErrors = Record<string, string>;

export type TerminalBacktestValidation = {
  errors: string[];
  fieldErrors: TerminalBacktestFieldErrors;
  numericParameters: Record<string, number>;
  normalizedSymbol: string;
  requestIdentity: MarketDataSymbolIdentity | null;
  canSubmit: boolean;
};

export type TerminalBacktestDraft = {
  symbol: string;
  identity?: InstrumentIdentityInput | null;
  chartRange: ChartRange;
  strategyId: BacktestStrategyId;
  parameterValues: Record<string, string>;
  commissionPerTrade: string;
  commissionBps: string;
  slippageBps: string;
  benchmarkMode: BacktestBenchmarkMode;
  capital?: PaperCapitalResponse | null;
};

export type TerminalBacktestComparisonCurveKind = 'strategy' | 'benchmark';

export type TerminalBacktestComparisonPoint = {
  time: string;
  timestamp: number;
  equity: number;
  drawdownPercent: number | null;
  normalizedReturnPercent: number;
};

export type TerminalBacktestComparisonCurve = {
  id: string;
  runId: string;
  kind: TerminalBacktestComparisonCurveKind;
  label: string;
  color: string;
  points: TerminalBacktestComparisonPoint[];
  finalEquity: number | null;
  totalReturnPercent: number | null;
};

export type TerminalBacktestComparisonRunSummary = {
  run: BacktestRunEnvelope;
  runId: string;
  label: string;
  symbol: string;
  strategyLabel: string;
  chartRangeLabel: string;
  capitalSourceLabel: string;
  statusLabel: string;
  sourceLabel: string;
  createdAtUtc: string;
  completedAtUtc: string | null;
  startUtc: string | null;
  endUtc: string | null;
  initialCapital: number | null;
  finalEquity: number | null;
  totalReturnPercent: number | null;
  maxDrawdownPercent: number | null;
  winRatePercent: number | null;
  tradeCount: number | null;
  benchmarkReturnPercent: number | null;
  benchmarkFinalEquity: number | null;
  strategyCurve: TerminalBacktestComparisonCurve;
  benchmarkCurve: TerminalBacktestComparisonCurve | null;
};

export type TerminalBacktestComparisonViewModel = {
  selectedRunIds: string[];
  eligibleRuns: BacktestRunEnvelope[];
  eligibleRunIds: string[];
  selectedSummaries: TerminalBacktestComparisonRunSummary[];
  strategyCurves: TerminalBacktestComparisonCurve[];
  benchmarkCurves: TerminalBacktestComparisonCurve[];
  curves: TerminalBacktestComparisonCurve[];
  hasMinimumSelection: boolean;
  emptyState: string;
};

export type TerminalBacktestWorkflow = {
  symbol: string;
  setSymbol: (value: string) => void;
  normalizedSymbol: string;
  requestIdentity: MarketDataSymbolIdentity | null;
  identitySummary: string;
  chartRange: ChartRange;
  chartRangeLabel: string;
  chartRangeDescription: string;
  setChartRange: (value: ChartRange) => void;
  strategies: readonly BacktestStrategyDefinition[];
  strategyId: BacktestStrategyId;
  strategyDefinition: BacktestStrategyDefinition;
  setStrategyId: (value: BacktestStrategyId) => void;
  parameterValues: Record<string, string>;
  setParameterValue: (name: string, value: string) => void;
  commissionPerTrade: string;
  setCommissionPerTrade: (value: string) => void;
  commissionBps: string;
  setCommissionBps: (value: string) => void;
  slippageBps: string;
  setSlippageBps: (value: string) => void;
  benchmarkMode: BacktestBenchmarkMode;
  setBenchmarkMode: (value: BacktestBenchmarkMode) => void;
  validation: TerminalBacktestValidation;
  capital: PaperCapitalResponse | null;
  capitalLoading: boolean;
  capitalError: string | null;
  capitalInput: string;
  setCapitalInput: (value: string) => void;
  capitalCurrency: string;
  setCapitalCurrency: (value: string) => void;
  updatingCapital: boolean;
  updateCapital: () => Promise<void>;
  reloadCapital: () => Promise<void>;
  runs: BacktestRunEnvelope[];
  selectedRunId: string | null;
  selectedRun: BacktestRunEnvelope | null;
  setSelectedRunId: (id: string | null) => void;
  comparison: TerminalBacktestComparisonViewModel;
  comparisonSelectedRunIds: string[];
  comparisonEligibleRuns: BacktestRunEnvelope[];
  comparisonSelectedSummaries: TerminalBacktestComparisonRunSummary[];
  comparisonCurves: TerminalBacktestComparisonCurve[];
  setComparisonSelectedRunIds: (ids: string[]) => void;
  toggleComparisonRunSelection: (id: string) => void;
  removeComparisonRunSelection: (id: string) => void;
  clearComparisonSelection: () => void;
  canCompareRun: (run?: BacktestRunEnvelope | null) => boolean;
  historyLoading: boolean;
  historyError: string | null;
  detailLoading: boolean;
  detailError: string | null;
  reloadHistory: () => Promise<void>;
  reloadSelectedRun: () => Promise<void>;
  streamState: BacktestStreamState;
  streamError: string | null;
  creatingRun: boolean;
  runActionPending: 'cancel' | 'retry' | null;
  actionError: string | null;
  canCreateRun: boolean;
  createRun: () => Promise<void>;
  cancelRun: (id?: string) => Promise<void>;
  retryRun: (id?: string) => Promise<void>;
  canCancelRun: (run?: BacktestRunEnvelope | null) => boolean;
  canRetryRun: (run?: BacktestRunEnvelope | null) => boolean;
  noOrderCopy: string;
  signalRCopy: string;
  capitalCopy: string;
  comparisonCopy: string;
};

const DEFAULT_HISTORY_LIMIT = 50;
const DEFAULT_STRATEGY_ID: BacktestStrategyId = 'sma-crossover';
const DEFAULT_CHART_RANGE: ChartRange = '1D';
const DEFAULT_BENCHMARK_MODE: BacktestBenchmarkMode = 'buy-and-hold';
const DEFAULT_CURRENCY = 'USD';

export function useTerminalBacktestWorkflow({
  initialChartRange = DEFAULT_CHART_RANGE,
  initialIdentity = null,
  initialSymbol = null,
  historyLimit = DEFAULT_HISTORY_LIMIT,
}: TerminalBacktestWorkflowOptions = {}): TerminalBacktestWorkflow {
  const initialNormalizedSymbol = normalizeOptionalSymbol(initialSymbol ?? initialIdentity?.symbol ?? '');
  const [symbol, setSymbolState] = useState(initialNormalizedSymbol);
  const [chartRange, setChartRange] = useState<ChartRange>(initialChartRange);
  const [identity, setIdentity] = useState<InstrumentIdentityInput | null>(initialIdentity);
  const [strategyId, setStrategyIdState] = useState<BacktestStrategyId>(DEFAULT_STRATEGY_ID);
  const [parameterValues, setParameterValues] = useState<Record<string, string>>(() => createDefaultBacktestParameterValues(DEFAULT_STRATEGY_ID));
  const [commissionPerTrade, setCommissionPerTrade] = useState('0');
  const [commissionBps, setCommissionBps] = useState('0');
  const [slippageBps, setSlippageBps] = useState('0');
  const [benchmarkMode, setBenchmarkMode] = useState<BacktestBenchmarkMode>(DEFAULT_BENCHMARK_MODE);
  const [capital, setCapital] = useState<PaperCapitalResponse | null>(null);
  const [capitalLoading, setCapitalLoading] = useState(true);
  const [capitalError, setCapitalError] = useState<string | null>(null);
  const [capitalInput, setCapitalInput] = useState('');
  const [capitalCurrency, setCapitalCurrency] = useState(DEFAULT_CURRENCY);
  const [updatingCapital, setUpdatingCapital] = useState(false);
  const [runs, setRuns] = useState<BacktestRunEnvelope[]>([]);
  const [selectedRunId, setSelectedRunIdState] = useState<string | null>(null);
  const [selectedRunDetail, setSelectedRunDetail] = useState<BacktestRunEnvelope | null>(null);
  const [comparisonSelectedRunIds, setComparisonSelectedRunIdsState] = useState<string[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [streamState, setStreamState] = useState<BacktestStreamState>('connecting');
  const [streamError, setStreamError] = useState<string | null>(null);
  const [creatingRun, setCreatingRun] = useState(false);
  const [runActionPending, setRunActionPending] = useState<'cancel' | 'retry' | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const reconnectingRef = useRef(false);
  const selectedRunIdRef = useRef<string | null>(null);

  useEffect(() => {
    selectedRunIdRef.current = selectedRunId;
  }, [selectedRunId]);

  useEffect(() => {
    setSymbolState(normalizeOptionalSymbol(initialSymbol ?? initialIdentity?.symbol ?? ''));
    setIdentity(initialIdentity);
  }, [initialIdentity, initialSymbol]);

  useEffect(() => {
    setChartRange(initialChartRange);
  }, [initialChartRange]);

  const loadCapital = useCallback(async () => {
    setCapitalLoading(true);
    setCapitalError(null);

    try {
      const response = await getPaperCapital();
      setCapital(response);
      setCapitalCurrency(response.currency || DEFAULT_CURRENCY);
      setCapitalInput(response.localCapital === null || response.localCapital === undefined ? '' : String(response.localCapital));
    } catch (caughtError) {
      setCapital(null);
      setCapitalError(formatBacktestWorkflowError(caughtError, 'Paper capital is unavailable.'));
    } finally {
      setCapitalLoading(false);
    }
  }, []);

  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    setHistoryError(null);

    try {
      const response = await listBacktestRuns(historyLimit);
      setRuns(response);
      setSelectedRunIdState((currentSelectedId) => currentSelectedId ?? response[0]?.id ?? null);
    } catch (caughtError) {
      setRuns([]);
      setHistoryError(formatBacktestWorkflowError(caughtError, 'Backtest run history is unavailable.'));
    } finally {
      setHistoryLoading(false);
    }
  }, [historyLimit]);

  const loadRunDetail = useCallback(async (id: string | null) => {
    if (!id) {
      setSelectedRunDetail(null);
      setDetailError(null);
      setDetailLoading(false);
      return;
    }

    setDetailLoading(true);
    setDetailError(null);

    try {
      const response = await getBacktestRun(id);
      setSelectedRunDetail(response);
      setRuns((currentRuns) => upsertBacktestRun(currentRuns, response));
    } catch (caughtError) {
      setSelectedRunDetail(null);
      setDetailError(formatBacktestWorkflowError(caughtError, 'Backtest run detail is unavailable.'));
    } finally {
      setDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadCapital();
    void loadHistory();
  }, [loadCapital, loadHistory]);

  useEffect(() => {
    void loadRunDetail(selectedRunId);
  }, [loadRunDetail, selectedRunId]);

  useEffect(() => {
    let active = true;
    let subscription: Awaited<ReturnType<typeof connectBacktestRunStream>> | null = null;

    async function connect() {
      setStreamError(null);

      try {
        subscription = await connectBacktestRunStream({
          onUpdate: (update) => {
            if (!active) {
              return;
            }

            setRuns((currentRuns) => mergeBacktestRunUpdateIntoRuns(currentRuns, update));
            setSelectedRunDetail((currentRun) => (currentRun && currentRun.id === update.id ? applyBacktestRunUpdate(currentRun, update) : currentRun));
          },
          onStateChange: (state) => {
            if (!active) {
              return;
            }

            setStreamState(state);
            if (state === 'reconnecting') {
              reconnectingRef.current = true;
            }

            if (state === 'connected' && reconnectingRef.current) {
              reconnectingRef.current = false;
              void loadHistory();
              void loadRunDetail(selectedRunIdRef.current);
            }
          },
        });
      } catch (caughtError) {
        if (active) {
          setStreamState('unavailable');
          setStreamError(formatBacktestWorkflowError(caughtError, 'Backtest status streaming is unavailable.'));
        }
      }
    }

    void connect();

    return () => {
      active = false;
      void subscription?.stop();
    };
  }, [loadHistory, loadRunDetail]);

  const strategyDefinition = useMemo(() => getBacktestStrategyDefinition(strategyId), [strategyId]);
  const normalizedSymbol = useMemo(() => normalizeOptionalSymbol(symbol), [symbol]);
  const validation = useMemo(
    () => validateBacktestDraft({
      symbol,
      identity,
      chartRange,
      strategyId,
      parameterValues,
      commissionPerTrade,
      commissionBps,
      slippageBps,
      benchmarkMode,
      capital,
    }),
    [benchmarkMode, capital, chartRange, commissionBps, commissionPerTrade, identity, parameterValues, slippageBps, strategyId, symbol],
  );
  const selectedRun = useMemo(
    () => selectedRunDetail ?? runs.find((run) => run.id === selectedRunId) ?? null,
    [runs, selectedRunDetail, selectedRunId],
  );
  const comparisonSourceRuns = useMemo(
    () => (selectedRunDetail ? upsertBacktestRun(runs, selectedRunDetail) : runs),
    [runs, selectedRunDetail],
  );
  const comparison = useMemo(
    () => buildBacktestComparisonViewModel(comparisonSourceRuns, comparisonSelectedRunIds),
    [comparisonSelectedRunIds, comparisonSourceRuns],
  );
  const comparisonEligibleRunIdKey = comparison.eligibleRunIds.join('|');
  const identitySummary = useMemo(
    () => formatBacktestIdentitySummary(normalizedSymbol, validation.requestIdentity, identity),
    [identity, normalizedSymbol, validation.requestIdentity],
  );

  useEffect(() => {
    setComparisonSelectedRunIdsState((currentRunIds) => pruneBacktestComparisonSelection(currentRunIds, comparison.eligibleRunIds));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [comparisonEligibleRunIdKey]);

  const canCreateRun = validation.canSubmit && !creatingRun && !capitalLoading && !updatingCapital;

  const setSymbol = useCallback((value: string) => {
    setSymbolState(value.toUpperCase());
    setActionError(null);
  }, []);

  const setStrategyId = useCallback((value: BacktestStrategyId) => {
    setStrategyIdState(value);
    setParameterValues(createDefaultBacktestParameterValues(value));
    setActionError(null);
  }, []);

  const setParameterValue = useCallback((name: string, value: string) => {
    setParameterValues((currentValues) => ({ ...currentValues, [name]: value }));
    setActionError(null);
  }, []);

  const setComparisonSelectedRunIds = useCallback((ids: string[]) => {
    setComparisonSelectedRunIdsState(pruneBacktestComparisonSelection(ids, comparison.eligibleRunIds));
    setActionError(null);
  }, [comparison.eligibleRunIds]);

  const toggleComparisonRunSelection = useCallback((id: string) => {
    setComparisonSelectedRunIdsState((currentRunIds) => {
      if (currentRunIds.includes(id)) {
        return currentRunIds.filter((runId) => runId !== id);
      }

      if (!comparison.eligibleRunIds.includes(id)) {
        return currentRunIds;
      }

      return [...currentRunIds, id];
    });
    setActionError(null);
  }, [comparison.eligibleRunIds]);

  const removeComparisonRunSelection = useCallback((id: string) => {
    setComparisonSelectedRunIdsState((currentRunIds) => currentRunIds.filter((runId) => runId !== id));
    setActionError(null);
  }, []);

  const clearComparisonSelection = useCallback(() => {
    setComparisonSelectedRunIdsState([]);
    setActionError(null);
  }, []);

  const updateCapital = useCallback(async () => {
    setUpdatingCapital(true);
    setActionError(null);

    try {
      const amount = parseOptionalNumber(capitalInput);
      if (amount === null || amount <= 0) {
        throw new Error('Local paper capital must be a positive number before it can support backtest creation.');
      }

      const response = await updateLocalPaperCapital({ amount, currency: capitalCurrency || DEFAULT_CURRENCY });
      setCapital(response);
      setCapitalCurrency(response.currency || DEFAULT_CURRENCY);
      setCapitalInput(response.localCapital === null || response.localCapital === undefined ? '' : String(response.localCapital));
    } catch (caughtError) {
      setActionError(formatBacktestWorkflowError(caughtError, 'Local paper capital update failed.'));
    } finally {
      setUpdatingCapital(false);
    }
  }, [capitalCurrency, capitalInput]);

  const createRun = useCallback(async () => {
    const currentValidation = validateBacktestDraft({
      symbol,
      identity,
      chartRange,
      strategyId,
      parameterValues,
      commissionPerTrade,
      commissionBps,
      slippageBps,
      benchmarkMode,
      capital,
    });

    if (!currentValidation.canSubmit) {
      setActionError(currentValidation.errors[0] ?? 'Backtest request is not ready.');
      return;
    }

    setCreatingRun(true);
    setActionError(null);

    try {
      const run = await createBacktestRun(createBacktestCreateRequest({
        symbol,
        identity,
        chartRange,
        strategyId,
        parameterValues,
        commissionPerTrade,
        commissionBps,
        slippageBps,
        benchmarkMode,
        capital,
      }));
      setRuns((currentRuns) => upsertBacktestRun(currentRuns, run));
      setSelectedRunIdState(run.id);
      setSelectedRunDetail(run);
    } catch (caughtError) {
      setActionError(formatBacktestWorkflowError(caughtError, 'Backtest run creation failed.'));
      if (caughtError instanceof BacktestClientError && caughtError.code === 'backtest-capital-unavailable') {
        void loadCapital();
      }
    } finally {
      setCreatingRun(false);
    }
  }, [benchmarkMode, capital, chartRange, commissionBps, commissionPerTrade, identity, loadCapital, parameterValues, slippageBps, strategyId, symbol]);

  const cancelRun = useCallback(async (id = selectedRunId ?? '') => {
    if (!id) {
      return;
    }

    setActionError(null);
    setRunActionPending('cancel');

    try {
      const run = await cancelBacktestRun(id);
      setRuns((currentRuns) => upsertBacktestRun(currentRuns, run));
      setSelectedRunIdState(run.id);
      setSelectedRunDetail(run);
    } catch (caughtError) {
      setActionError(formatBacktestWorkflowError(caughtError, 'Backtest cancellation failed.'));
    } finally {
      setRunActionPending(null);
    }
  }, [selectedRunId]);

  const retryRun = useCallback(async (id = selectedRunId ?? '') => {
    if (!id) {
      return;
    }

    setActionError(null);
    setRunActionPending('retry');

    try {
      const run = await retryBacktestRun(id);
      setRuns((currentRuns) => upsertBacktestRun(currentRuns, run));
      setSelectedRunIdState(run.id);
      setSelectedRunDetail(run);
    } catch (caughtError) {
      setActionError(formatBacktestWorkflowError(caughtError, 'Backtest retry failed.'));
      if (caughtError instanceof BacktestClientError && caughtError.code === 'backtest-capital-unavailable') {
        void loadCapital();
      }
    } finally {
      setRunActionPending(null);
    }
  }, [loadCapital, selectedRunId]);

  const reloadSelectedRun = useCallback(async () => {
    await loadRunDetail(selectedRunId);
  }, [loadRunDetail, selectedRunId]);

  return {
    symbol,
    setSymbol,
    normalizedSymbol,
    requestIdentity: validation.requestIdentity,
    identitySummary,
    chartRange,
    chartRangeLabel: CHART_RANGE_LABELS[chartRange],
    chartRangeDescription: CHART_RANGE_DESCRIPTIONS[chartRange],
    setChartRange,
    strategies: BACKTEST_STRATEGY_DEFINITIONS,
    strategyId,
    strategyDefinition,
    setStrategyId,
    parameterValues,
    setParameterValue,
    commissionPerTrade,
    setCommissionPerTrade,
    commissionBps,
    setCommissionBps,
    slippageBps,
    setSlippageBps,
    benchmarkMode,
    setBenchmarkMode,
    validation,
    capital,
    capitalLoading,
    capitalError,
    capitalInput,
    setCapitalInput,
    capitalCurrency,
    setCapitalCurrency,
    updatingCapital,
    updateCapital,
    reloadCapital: loadCapital,
    runs,
    selectedRunId,
    selectedRun,
    setSelectedRunId: setSelectedRunIdState,
    comparison,
    comparisonSelectedRunIds: comparison.selectedRunIds,
    comparisonEligibleRuns: comparison.eligibleRuns,
    comparisonSelectedSummaries: comparison.selectedSummaries,
    comparisonCurves: comparison.curves,
    setComparisonSelectedRunIds,
    toggleComparisonRunSelection,
    removeComparisonRunSelection,
    clearComparisonSelection,
    canCompareRun: canCompareBacktestRun,
    historyLoading,
    historyError,
    detailLoading,
    detailError,
    reloadHistory: loadHistory,
    reloadSelectedRun,
    streamState,
    streamError,
    creatingRun,
    runActionPending,
    actionError,
    canCreateRun,
    createRun,
    cancelRun,
    retryRun,
    canCancelRun: canCancelBacktestRun,
    canRetryRun: canRetryBacktestRun,
    noOrderCopy: TERMINAL_BACKTEST_NO_ORDER_COPY,
    signalRCopy: TERMINAL_BACKTEST_SIGNALR_COPY,
    capitalCopy: TERMINAL_BACKTEST_CAPITAL_COPY,
    comparisonCopy: TERMINAL_BACKTEST_COMPARISON_COPY,
  };
}

export function getBacktestStrategyDefinition(strategyId: BacktestStrategyId): BacktestStrategyDefinition {
  return BACKTEST_STRATEGY_DEFINITIONS.find((strategy) => strategy.id === strategyId) ?? BACKTEST_STRATEGY_DEFINITIONS[0];
}

export function createDefaultBacktestParameterValues(strategyId: BacktestStrategyId): Record<string, string> {
  return Object.fromEntries(
    getBacktestStrategyDefinition(strategyId).parameters.map((parameter) => [parameter.name, String(parameter.defaultValue)]),
  );
}

export function validateBacktestDraft(draft: TerminalBacktestDraft): TerminalBacktestValidation {
  const errors: string[] = [];
  const fieldErrors: TerminalBacktestFieldErrors = {};
  const normalizedSymbol = normalizeOptionalSymbol(draft.symbol);
  const requestIdentity = resolveBacktestRequestIdentity(draft.identity, normalizedSymbol);
  const numericParameters: Record<string, number> = {};
  const strategy = getBacktestStrategyDefinition(draft.strategyId);

  if (!normalizedSymbol) {
    fieldErrors.symbol = 'Enter a single stock symbol before creating a backtest.';
  } else if (!/^[A-Z0-9][A-Z0-9._-]{0,31}$/.test(normalizedSymbol)) {
    fieldErrors.symbol = "Symbols may contain only letters, digits, '.', '-', or '_' and must start with a letter or digit.";
  }

  for (const parameter of strategy.parameters) {
    const key = `parameter:${parameter.name}`;
    const parsed = parseRequiredNumber(draft.parameterValues[parameter.name]);
    if (parsed === null) {
      fieldErrors[key] = `${parameter.displayName} must be numeric.`;
      continue;
    }

    if (parameter.valueType === 'integer' && !Number.isInteger(parsed)) {
      fieldErrors[key] = `${parameter.displayName} must be a whole number.`;
      continue;
    }

    if (parsed < parameter.minimumValue || parsed > parameter.maximumValue) {
      fieldErrors[key] = `${parameter.displayName} must be between ${parameter.minimumValue} and ${parameter.maximumValue}.`;
      continue;
    }

    numericParameters[parameter.name] = parameter.valueType === 'integer' ? Math.trunc(parsed) : roundFourDecimals(parsed);
  }

  if (draft.strategyId === 'sma-crossover' && numericParameters.shortWindow >= numericParameters.longWindow) {
    fieldErrors['parameter:shortWindow'] = 'Short SMA window must be less than the long SMA window.';
  }

  if (draft.strategyId === 'rsi-mean-reversion' && numericParameters.oversoldThreshold >= numericParameters.overboughtThreshold) {
    fieldErrors['parameter:oversoldThreshold'] = 'Oversold threshold must be less than the overbought threshold.';
  }

  const commissionPerTrade = parseRequiredNumber(draft.commissionPerTrade);
  if (commissionPerTrade === null || commissionPerTrade < 0 || commissionPerTrade > 1000) {
    fieldErrors.commissionPerTrade = 'Commission per trade must be a number from 0 to 1000.';
  }

  const commissionBps = parseRequiredNumber(draft.commissionBps);
  if (commissionBps === null || commissionBps < 0 || commissionBps > 1000) {
    fieldErrors.commissionBps = 'Commission bps must be a number from 0 to 1000.';
  }

  const slippage = parseRequiredNumber(draft.slippageBps);
  if (slippage === null || slippage < 0 || slippage > 1000) {
    fieldErrors.slippageBps = 'Slippage bps must be a number from 0 to 1000.';
  }

  if (!draft.capital || draft.capital.effectiveCapital === null || draft.capital.effectiveCapital <= 0 || draft.capital.source === 'unavailable') {
    fieldErrors.capital = 'An effective paper-capital source is required before a run can be created.';
  }

  errors.push(...Object.values(fieldErrors));

  return {
    errors,
    fieldErrors,
    numericParameters,
    normalizedSymbol,
    requestIdentity,
    canSubmit: errors.length === 0,
  };
}

export function createBacktestCreateRequest(draft: TerminalBacktestDraft): BacktestCreateRequest {
  const validation = validateBacktestDraft(draft);
  if (!validation.canSubmit) {
    throw new Error(validation.errors[0] ?? 'Backtest request is not valid.');
  }

  return {
    symbol: validation.requestIdentity,
    symbolCode: validation.normalizedSymbol,
    strategyId: draft.strategyId,
    parameters: validation.numericParameters,
    chartRange: draft.chartRange,
    costModel: {
      commissionPerTrade: roundFourDecimals(parseRequiredNumber(draft.commissionPerTrade) ?? 0),
      commissionBps: roundFourDecimals(parseRequiredNumber(draft.commissionBps) ?? 0),
      currency: draft.capital?.currency ?? DEFAULT_CURRENCY,
    },
    slippageBps: roundFourDecimals(parseRequiredNumber(draft.slippageBps) ?? 0),
    benchmarkMode: draft.benchmarkMode,
  };
}

export function mergeBacktestRunUpdateIntoRuns(runs: BacktestRunEnvelope[], update: BacktestRunUpdatePayload): BacktestRunEnvelope[] {
  let matched = false;
  const merged = runs.map((run) => {
    if (run.id !== update.id) {
      return run;
    }

    matched = true;
    return applyBacktestRunUpdate(run, update);
  });

  return matched ? sortBacktestRuns(merged) : runs;
}

export function applyBacktestRunUpdate(run: BacktestRunEnvelope, update: BacktestRunUpdatePayload): BacktestRunEnvelope {
  return {
    ...run,
    status: update.status,
    sourceRunId: update.sourceRunId ?? run.sourceRunId ?? null,
    updatedAtUtc: update.updatedAtUtc,
    startedAtUtc: update.startedAtUtc ?? run.startedAtUtc ?? null,
    completedAtUtc: update.completedAtUtc ?? run.completedAtUtc ?? null,
    error: update.error ?? null,
    result: update.result ?? run.result ?? null,
  };
}

export function upsertBacktestRun(runs: BacktestRunEnvelope[], run: BacktestRunEnvelope): BacktestRunEnvelope[] {
  const withoutRun = runs.filter((candidate) => candidate.id !== run.id);
  return sortBacktestRuns([run, ...withoutRun]);
}

export function sortBacktestRuns(runs: BacktestRunEnvelope[]): BacktestRunEnvelope[] {
  return [...runs].sort((left, right) => Date.parse(right.createdAtUtc) - Date.parse(left.createdAtUtc));
}

export function canCompareBacktestRun(run?: BacktestRunEnvelope | null): boolean {
  if (!run || !isBacktestStatus(run.status, 'completed') || !run.result?.backtest) {
    return false;
  }

  return normalizeBacktestEquitySeries(run.result.equityCurve, run.result.backtest.initialCapital).length > 0;
}

export function getBacktestComparisonEligibleRuns(runs: BacktestRunEnvelope[]): BacktestRunEnvelope[] {
  return sortBacktestRuns(runs).filter((run) => canCompareBacktestRun(run));
}

export function pruneBacktestComparisonSelection(selectedRunIds: readonly string[], eligibleRunIds: readonly string[]): string[] {
  const eligible = new Set(eligibleRunIds);
  const seen = new Set<string>();
  const pruned: string[] = [];

  for (const runId of selectedRunIds) {
    if (!eligible.has(runId) || seen.has(runId)) {
      continue;
    }

    seen.add(runId);
    pruned.push(runId);
  }

  return pruned;
}

export function buildBacktestComparisonViewModel(
  runs: BacktestRunEnvelope[],
  selectedRunIds: readonly string[],
): TerminalBacktestComparisonViewModel {
  const eligibleRuns = getBacktestComparisonEligibleRuns(runs);
  const eligibleRunIds = eligibleRuns.map((run) => run.id);
  const selectedIds = pruneBacktestComparisonSelection(selectedRunIds, eligibleRunIds);
  const eligibleById = new Map(eligibleRuns.map((run) => [run.id, run]));
  const selectedSummaries = selectedIds
    .map((runId) => createBacktestComparisonRunSummary(eligibleById.get(runId) ?? null))
    .filter((summary): summary is TerminalBacktestComparisonRunSummary => summary !== null);
  const strategyCurves = selectedSummaries.map((summary) => summary.strategyCurve);
  const benchmarkCurves = selectedSummaries
    .map((summary) => summary.benchmarkCurve)
    .filter((curve): curve is TerminalBacktestComparisonCurve => curve !== null);
  const selectedCount = selectedSummaries.length;

  return {
    selectedRunIds: selectedIds,
    eligibleRuns,
    eligibleRunIds,
    selectedSummaries,
    strategyCurves,
    benchmarkCurves,
    curves: [...strategyCurves, ...benchmarkCurves],
    hasMinimumSelection: selectedCount >= 2,
    emptyState: selectedCount === 0
      ? 'Select at least two completed saved runs with persisted equity curves to compare strategy and buy-and-hold performance.'
      : selectedCount === 1
        ? 'Select one more completed saved run to enable side-by-side comparison.'
        : '',
  };
}

export function createBacktestComparisonRunSummary(run?: BacktestRunEnvelope | null): TerminalBacktestComparisonRunSummary | null {
  const result = run?.result ?? null;
  const backtest = result?.backtest ?? null;
  if (!run || !canCompareBacktestRun(run) || !result || !backtest) {
    return null;
  }

  const strategyCurve = createBacktestComparisonCurve(run, 'strategy');
  if (!strategyCurve) {
    return null;
  }

  const benchmarkCurve = createBacktestComparisonCurve(run, 'benchmark');
  const symbol = result.symbol?.symbol || run.request.symbol.symbol;
  const strategyLabel = formatBacktestStrategyDisplayName(run.request.strategyId);
  const chartRangeLabel = formatBacktestChartRangeLabel(run.request.chartRange);
  const sourceLabel = `${result.source.marketDataSource || 'market data source'} · ${result.engine.displayName || result.engine.provider}`;

  return {
    run,
    runId: run.id,
    label: `${symbol} · ${strategyLabel} · ${chartRangeLabel}`,
    symbol,
    strategyLabel,
    chartRangeLabel,
    capitalSourceLabel: formatBacktestCapitalSource(run.capital.capitalSource),
    statusLabel: formatBacktestStatusLabel(run.status),
    sourceLabel,
    createdAtUtc: run.createdAtUtc,
    completedAtUtc: run.completedAtUtc ?? null,
    startUtc: backtest.startUtc ?? null,
    endUtc: backtest.endUtc ?? null,
    initialCapital: backtest.initialCapital,
    finalEquity: backtest.finalEquity,
    totalReturnPercent: backtest.totalReturnPercent,
    maxDrawdownPercent: backtest.maxDrawdownPercent,
    winRatePercent: backtest.winRatePercent,
    tradeCount: backtest.tradeCount,
    benchmarkReturnPercent: result.benchmark?.totalReturnPercent ?? null,
    benchmarkFinalEquity: result.benchmark?.finalEquity ?? null,
    strategyCurve,
    benchmarkCurve,
  };
}

export function createBacktestComparisonCurve(
  run: BacktestRunEnvelope,
  kind: TerminalBacktestComparisonCurveKind,
): TerminalBacktestComparisonCurve | null {
  const result = run.result;
  if (!result) {
    return null;
  }

  const sourcePoints = kind === 'strategy' ? result.equityCurve : result.benchmark?.equityCurve;
  const baseline = kind === 'strategy'
    ? result.backtest?.initialCapital ?? run.capital.initialCapital
    : result.benchmark?.initialCapital ?? result.backtest?.initialCapital ?? run.capital.initialCapital;
  const points = normalizeBacktestEquitySeries(sourcePoints, baseline);
  if (points.length === 0) {
    return null;
  }

  const finalPoint = points[points.length - 1];
  const finalEquity = kind === 'strategy'
    ? result.backtest?.finalEquity ?? finalPoint.equity
    : result.benchmark?.finalEquity ?? finalPoint.equity;
  const totalReturnPercent = kind === 'strategy'
    ? result.backtest?.totalReturnPercent ?? finalPoint.normalizedReturnPercent
    : result.benchmark?.totalReturnPercent ?? finalPoint.normalizedReturnPercent;

  return {
    id: `${run.id}:${kind}`,
    runId: run.id,
    kind,
    label: formatBacktestComparisonCurveLabel(run, kind),
    color: getBacktestComparisonCurveColor(run.id, kind),
    points,
    finalEquity,
    totalReturnPercent,
  };
}

export function normalizeBacktestEquitySeries(
  points: readonly BacktestResultEquityCurvePointEnvelope[] | null | undefined,
  fallbackInitialEquity?: number | null,
): TerminalBacktestComparisonPoint[] {
  const normalizedPoints: Omit<TerminalBacktestComparisonPoint, 'normalizedReturnPercent'>[] = [];

  for (const point of points ?? []) {
    const timestamp = Date.parse(point.time);
    if (!Number.isFinite(timestamp) || !Number.isFinite(point.equity)) {
      continue;
    }

    normalizedPoints.push({
      time: point.time,
      timestamp,
      equity: point.equity,
      drawdownPercent: Number.isFinite(point.drawdownPercent) ? point.drawdownPercent : null,
    });
  }

  normalizedPoints.sort((left, right) => left.timestamp - right.timestamp);

  const fallback = typeof fallbackInitialEquity === 'number' && Number.isFinite(fallbackInitialEquity) && fallbackInitialEquity > 0
    ? fallbackInitialEquity
    : null;
  const baseline = fallback ?? normalizedPoints.find((point) => point.equity > 0)?.equity ?? null;
  if (!baseline) {
    return [];
  }

  return normalizedPoints.map((point) => ({
    ...point,
    normalizedReturnPercent: roundFourDecimals(((point.equity - baseline) / baseline) * 100),
  }));
}

export function getBacktestComparisonCurveColor(runId: string, kind: TerminalBacktestComparisonCurveKind): string {
  const palette = kind === 'strategy' ? BACKTEST_COMPARISON_STRATEGY_COLORS : BACKTEST_COMPARISON_BENCHMARK_COLORS;
  return palette[hashBacktestComparisonKey(`${kind}:${runId}`) % palette.length];
}

export function formatBacktestComparisonCurveLabel(run: BacktestRunEnvelope, kind: TerminalBacktestComparisonCurveKind): string {
  const symbol = run.result?.symbol?.symbol || run.request.symbol.symbol;
  if (kind === 'benchmark') {
    return `${symbol} ${run.result?.benchmark?.label || 'buy-and-hold'} benchmark`;
  }

  return `${symbol} ${formatBacktestStrategyDisplayName(run.request.strategyId)} strategy`;
}

export function getBacktestComparisonEligibilityCopy(run?: BacktestRunEnvelope | null): string {
  if (!run) {
    return 'No saved run is available for comparison.';
  }

  if (!isBacktestStatus(run.status, 'completed')) {
    return 'Comparison is available only after a saved run reaches completed status.';
  }

  if (!run.result?.backtest) {
    return 'Completed runs need a persisted result summary before comparison.';
  }

  if (!canCompareBacktestRun(run)) {
    return 'Completed runs need persisted strategy equity curve points before comparison.';
  }

  return 'Selectable completed run with persisted result and strategy equity curve data.';
}

export function canCancelBacktestRun(run?: BacktestRunEnvelope | null): boolean {
  return Boolean(run && (isBacktestStatus(run.status, 'queued') || isBacktestStatus(run.status, 'running')));
}

export function canRetryBacktestRun(run?: BacktestRunEnvelope | null): boolean {
  return Boolean(run && (isBacktestStatus(run.status, 'failed') || isBacktestStatus(run.status, 'cancelled')));
}

export function formatBacktestWorkflowError(caughtError: unknown, fallback: string): string {
  return caughtError instanceof Error ? caughtError.message : fallback;
}

export function formatBacktestStatusLabel(status: BacktestRunStatus): string {
  const normalized = status.trim().toLowerCase();
  if (normalized === 'queued') {
    return 'Queued';
  }

  if (normalized === 'running') {
    return 'Running';
  }

  if (normalized === 'completed') {
    return 'Completed';
  }

  if (normalized === 'failed') {
    return 'Failed';
  }

  if (normalized === 'cancelled') {
    return 'Cancelled';
  }

  return status;
}

export function formatBacktestCapitalSource(source: string | null | undefined): string {
  if (source === 'ibkr-paper-balance') {
    return 'IBKR paper balance';
  }

  if (source === 'local-paper-ledger') {
    return 'Local paper capital';
  }

  if (source === 'unavailable') {
    return 'Unavailable';
  }

  return source || 'Unknown';
}

export function formatBacktestStrategyDisplayName(strategyId: BacktestStrategyId | string): string {
  return BACKTEST_STRATEGY_DEFINITIONS.find((strategy) => strategy.id === strategyId)?.displayName ?? strategyId;
}

export function formatBacktestChartRangeLabel(chartRange: ChartRange | string): string {
  return CHART_RANGE_LABELS[chartRange as ChartRange] ?? chartRange;
}

function resolveBacktestRequestIdentity(identity: InstrumentIdentityInput | null | undefined, normalizedSymbol: string): MarketDataSymbolIdentity | null {
  if (!identity || !normalizedSymbol) {
    return null;
  }

  const normalizedIdentity = normalizeInstrumentIdentity(identity);
  if (normalizedIdentity.symbol !== normalizedSymbol) {
    return null;
  }

  return toMarketDataSymbolIdentity(normalizedIdentity);
}

function toMarketDataSymbolIdentity(identity: NormalizedInstrumentIdentity): MarketDataSymbolIdentity {
  return {
    symbol: identity.symbol,
    provider: identity.provider,
    providerSymbolId: identity.providerSymbolId,
    assetClass: identity.assetClass,
    exchange: identity.exchange ?? '',
    currency: identity.currency,
  };
}

function normalizeOptionalSymbol(symbol: string | null | undefined): string {
  return symbol?.trim().toUpperCase() ?? '';
}

function parseRequiredNumber(value: string | number | null | undefined): number | null {
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : null;
  }

  const trimmed = value?.trim();
  if (!trimmed) {
    return null;
  }

  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

function parseOptionalNumber(value: string | number | null | undefined): number | null {
  const parsed = parseRequiredNumber(value);
  return parsed === null ? null : roundFourDecimals(parsed);
}

function roundFourDecimals(value: number): number {
  return Math.round(value * 10000) / 10000;
}

function isBacktestStatus(status: BacktestRunStatus, expected: string): boolean {
  return status.trim().toLowerCase() === expected;
}

function hashBacktestComparisonKey(input: string): number {
  let hash = 0;
  for (let index = 0; index < input.length; index += 1) {
    hash = ((hash * 31) + input.charCodeAt(index)) | 0;
  }

  return Math.abs(hash);
}

function formatBacktestIdentitySummary(
  symbol: string,
  requestIdentity: MarketDataSymbolIdentity | null,
  rawIdentity: InstrumentIdentityInput | null,
): string {
  if (!symbol) {
    return 'Enter one stock symbol, or open Backtest from a chart/market-monitor row to carry exact provider identity.';
  }

  if (!requestIdentity) {
    return rawIdentity
      ? `${symbol} will run as a manual symbol because the edited symbol no longer matches the exact handoff identity.`
      : `${symbol} will run with a symbol-only request; server-side market data remains behind ATrade.Api.`;
  }

  const provider = requestIdentity.provider.toUpperCase();
  const providerId = requestIdentity.providerSymbolId ? ` · provider id ${requestIdentity.providerSymbolId}` : '';
  const exchange = requestIdentity.exchange ? ` · market ${requestIdentity.exchange}` : '';
  return `${requestIdentity.symbol} exact identity: provider ${provider}${providerId}${exchange} · ${requestIdentity.currency} · ${requestIdentity.assetClass}.`;
}
