'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';

import { AnalysisClientError, getAnalysisEngines, runAnalysis as runProviderNeutralAnalysis } from './analysisClient';
import { normalizeInstrumentIdentity, type InstrumentIdentityInput, type NormalizedInstrumentIdentity } from './instrumentIdentity';
import { CHART_RANGE_DESCRIPTIONS, CHART_RANGE_LABELS, type ChartRange, type MarketDataSymbolIdentity } from '../types/marketData';
import type { AnalysisEngineDescriptor, AnalysisResult, RunAnalysisRequest } from '../types/analysis';

export const TERMINAL_ANALYSIS_NO_ORDER_COPY = 'Analysis only — no brokerage routing or automatic order placement.';
export const TERMINAL_ANALYSIS_PROVIDER_NEUTRAL_COPY = 'Provider-neutral analysis uses ATrade.Api /api/analysis/engines and /api/analysis/run; LEAN and future engines stay behind the backend analysis provider seam.';
export const TERMINAL_ANALYSIS_NO_ENGINE_HINT = 'No analysis engine is configured. Set ATRADE_ANALYSIS_ENGINE=Lean in ignored .env to enable analysis.';

export type TerminalAnalysisState = 'checking' | 'ready' | 'not-configured' | 'unavailable' | 'running' | 'failed';

export type TerminalAnalysisWorkflowOptions = {
  symbol: string;
  chartRange: ChartRange;
  candleSource?: string | null;
  identity?: InstrumentIdentityInput | null;
  strategyName?: string;
};

export type TerminalAnalysisWorkflow = {
  symbol: string;
  chartRange: ChartRange;
  chartRangeLabel: string;
  chartRangeDescription: string;
  sourceLabel: string;
  requestIdentity: MarketDataSymbolIdentity | null;
  engines: AnalysisEngineDescriptor[];
  enginesLoading: boolean;
  configuredEngine: AnalysisEngineDescriptor | null;
  runnableEngine: AnalysisEngineDescriptor | null;
  engineState: TerminalAnalysisState;
  engineStateLabel: string;
  unavailableMessage: string | null;
  running: boolean;
  result: AnalysisResult | null;
  error: string | null;
  canRun: boolean;
  noOrderCopy: string;
  providerNeutralCopy: string;
  runAnalysis: () => Promise<void>;
};

export function useTerminalAnalysisWorkflow({
  symbol,
  chartRange,
  candleSource = null,
  identity = null,
  strategyName = 'moving-average-crossover',
}: TerminalAnalysisWorkflowOptions): TerminalAnalysisWorkflow {
  const normalizedSymbol = symbol.trim().toUpperCase();
  const requestIdentity = useMemo(
    () => (identity ? toMarketDataSymbolIdentity(normalizeInstrumentIdentity({ ...identity, symbol: normalizedSymbol })) : null),
    [identity, normalizedSymbol],
  );
  const [engines, setEngines] = useState<AnalysisEngineDescriptor[]>([]);
  const [enginesLoading, setEnginesLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadEngines() {
      setEnginesLoading(true);
      setError(null);

      try {
        const descriptors = await getAnalysisEngines();
        if (active) {
          setEngines(descriptors);
        }
      } catch (caughtError) {
        if (active) {
          setError(caughtError instanceof Error ? caughtError.message : 'Analysis engine discovery is unavailable.');
        }
      } finally {
        if (active) {
          setEnginesLoading(false);
        }
      }
    }

    void loadEngines();

    return () => {
      active = false;
    };
  }, []);

  const configuredEngine = useMemo(
    () => engines.find((engine) => engine.metadata.engineId !== 'not-configured') ?? null,
    [engines],
  );
  const runnableEngine = useMemo(
    () => engines.find((engine) => engine.metadata.state === 'available' && engine.metadata.engineId !== 'not-configured') ?? null,
    [engines],
  );
  const unavailableMessage = useMemo(
    () => createTerminalAnalysisUnavailableMessage({
      configuredEngine,
      engines,
      enginesLoading,
      error,
      runnableEngine,
    }),
    [configuredEngine, engines, enginesLoading, error, runnableEngine],
  );
  const engineState = useMemo(
    () => getTerminalAnalysisState({
      configuredEngine,
      enginesLoading,
      error,
      runnableEngine,
      running,
    }),
    [configuredEngine, enginesLoading, error, runnableEngine, running],
  );
  const engineStateLabel = useMemo(
    () => getTerminalAnalysisStateLabel({
      configuredEngine,
      engineState,
      runnableEngine,
    }),
    [configuredEngine, engineState, runnableEngine],
  );
  const sourceLabel = useMemo(() => formatAnalysisSourceLabel(candleSource), [candleSource]);

  const handleRunAnalysis = useCallback(async () => {
    if (!runnableEngine) {
      return;
    }

    setRunning(true);
    setError(null);
    setResult(null);

    try {
      const analysis = await runProviderNeutralAnalysis(createTerminalAnalysisRunRequest({
        chartRange,
        engineId: runnableEngine.metadata.engineId,
        identity: requestIdentity,
        strategyName,
        symbol: normalizedSymbol,
      }));
      setResult(analysis);
    } catch (caughtError) {
      if (caughtError instanceof AnalysisClientError) {
        setResult(caughtError.result ?? null);
        setError(caughtError.message);
      } else {
        setError(caughtError instanceof Error ? caughtError.message : 'Analysis request failed.');
      }
    } finally {
      setRunning(false);
    }
  }, [chartRange, normalizedSymbol, requestIdentity, runnableEngine, strategyName]);

  return {
    symbol: normalizedSymbol,
    chartRange,
    chartRangeLabel: CHART_RANGE_LABELS[chartRange],
    chartRangeDescription: CHART_RANGE_DESCRIPTIONS[chartRange],
    sourceLabel,
    requestIdentity,
    engines,
    enginesLoading,
    configuredEngine,
    runnableEngine,
    engineState,
    engineStateLabel,
    unavailableMessage,
    running,
    result,
    error,
    canRun: Boolean(runnableEngine && !running && !enginesLoading),
    noOrderCopy: TERMINAL_ANALYSIS_NO_ORDER_COPY,
    providerNeutralCopy: TERMINAL_ANALYSIS_PROVIDER_NEUTRAL_COPY,
    runAnalysis: handleRunAnalysis,
  };
}

export function createTerminalAnalysisRunRequest({
  chartRange,
  engineId,
  identity,
  strategyName,
  symbol,
}: {
  chartRange: ChartRange;
  engineId: string;
  identity: MarketDataSymbolIdentity | null;
  strategyName: string;
  symbol: string;
}): RunAnalysisRequest {
  return {
    symbol: identity,
    symbolCode: symbol,
    timeframe: chartRange,
    engineId,
    strategyName,
  };
}

export function createTerminalAnalysisUnavailableMessage({
  configuredEngine,
  engines,
  enginesLoading,
  error,
  runnableEngine,
}: {
  configuredEngine: AnalysisEngineDescriptor | null;
  engines: AnalysisEngineDescriptor[];
  enginesLoading: boolean;
  error: string | null;
  runnableEngine: AnalysisEngineDescriptor | null;
}): string | null {
  if (enginesLoading) {
    return null;
  }

  if (error) {
    return error;
  }

  if (runnableEngine) {
    return null;
  }

  if (!configuredEngine) {
    const descriptor = engines[0];
    return descriptor?.metadata.message ?? TERMINAL_ANALYSIS_NO_ENGINE_HINT;
  }

  return configuredEngine.metadata.message ?? `${configuredEngine.metadata.displayName} is unavailable.`;
}

function getTerminalAnalysisState({
  configuredEngine,
  enginesLoading,
  error,
  runnableEngine,
  running,
}: {
  configuredEngine: AnalysisEngineDescriptor | null;
  enginesLoading: boolean;
  error: string | null;
  runnableEngine: AnalysisEngineDescriptor | null;
  running: boolean;
}): TerminalAnalysisState {
  if (running) {
    return 'running';
  }

  if (enginesLoading) {
    return 'checking';
  }

  if (error) {
    return 'failed';
  }

  if (runnableEngine) {
    return 'ready';
  }

  if (!configuredEngine) {
    return 'not-configured';
  }

  return 'unavailable';
}

function getTerminalAnalysisStateLabel({
  configuredEngine,
  engineState,
  runnableEngine,
}: {
  configuredEngine: AnalysisEngineDescriptor | null;
  engineState: TerminalAnalysisState;
  runnableEngine: AnalysisEngineDescriptor | null;
}): string {
  if (engineState === 'checking') {
    return 'checking…';
  }

  if (engineState === 'running') {
    return 'running…';
  }

  if (runnableEngine) {
    return runnableEngine.metadata.displayName;
  }

  if (configuredEngine) {
    return configuredEngine.metadata.state;
  }

  if (engineState === 'failed') {
    return 'discovery failed';
  }

  return 'not configured';
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

function formatAnalysisSourceLabel(source: string | null | undefined): string {
  if (!source) {
    return 'the market-data provider';
  }

  return source.includes('ibkr') ? 'IBKR/iBeam' : source;
}
