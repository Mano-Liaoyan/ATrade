'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { AnalysisClientError, getAnalysisEngines, runAnalysis } from '../lib/analysisClient';
import type { AnalysisEngineDescriptor, AnalysisMetric, AnalysisResult, AnalysisSignal } from '../types/analysis';
import { CHART_RANGE_DESCRIPTIONS, CHART_RANGE_LABELS, type ChartRange } from '../types/marketData';

type AnalysisPanelProps = {
  symbol: string;
  chartRange: ChartRange;
  candleSource?: string | null;
};

export function AnalysisPanel({ symbol, chartRange, candleSource }: AnalysisPanelProps) {
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
    () => engines.find((engine) => engine.metadata.state === 'available' && engine.metadata.engineId !== 'not-configured') ?? null,
    [engines],
  );

  const unavailableMessage = useMemo(() => {
    if (enginesLoading) {
      return null;
    }

    if (error) {
      return error;
    }

    if (!configuredEngine) {
      const descriptor = engines[0];
      return descriptor?.metadata.message ?? 'No analysis engine is configured. Set ATRADE_ANALYSIS_ENGINE=Lean in ignored .env to enable analysis.';
    }

    if (configuredEngine.metadata.state !== 'available') {
      return configuredEngine.metadata.message ?? `${configuredEngine.metadata.displayName} is unavailable.`;
    }

    return null;
  }, [configuredEngine, engines, enginesLoading, error]);

  const handleRunAnalysis = useCallback(async () => {
    if (!configuredEngine) {
      return;
    }

    setRunning(true);
    setError(null);
    setResult(null);

    try {
      const analysis = await runAnalysis({
        symbolCode: symbol,
        timeframe: chartRange,
        engineId: configuredEngine.metadata.engineId,
        strategyName: 'moving-average-crossover',
      });
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
  }, [configuredEngine, symbol, chartRange]);

  return (
    <section className="analysis-panel" data-testid="analysis-panel" aria-live="polite">
      <div className="panel-heading analysis-heading">
        <div>
          <p className="eyebrow">Analysis engine</p>
          <h2>Provider-neutral signals</h2>
        </div>
        <span className={configuredEngine ? 'pill analysis-pill--ready' : 'pill analysis-pill--muted'} data-testid="analysis-engine-state">
          {enginesLoading ? 'checking…' : configuredEngine ? configuredEngine.metadata.displayName : 'not configured'}
        </span>
      </div>

      <p className="analysis-copy">
        Run an analysis-only backtest over the current {CHART_RANGE_LABELS[chartRange]} lookback candles ({CHART_RANGE_DESCRIPTIONS[chartRange].toLowerCase()}) from {formatSourceLabel(candleSource)}. Results are signals and metrics only;
        this panel never places orders or starts automated trading.
      </p>

      {unavailableMessage ? (
        <div className="analysis-unavailable" data-testid="analysis-unavailable" role="status">
          <strong>Analysis unavailable.</strong>
          <p>{unavailableMessage}</p>
        </div>
      ) : null}

      <div className="analysis-actions">
        <button
          className="primary-button"
          type="button"
          data-testid="analysis-run-button"
          disabled={!configuredEngine || running || enginesLoading}
          onClick={() => void handleRunAnalysis()}
        >
          {running ? 'Running analysis…' : `Run ${configuredEngine?.metadata.provider ?? 'analysis'}`}
        </button>
        <span data-testid="analysis-no-automation-note">Analysis only — no brokerage routing or automatic order placement.</span>
      </div>

      {running ? <div className="loading-state" role="status">Waiting for the configured analysis runtime…</div> : null}
      {error && !unavailableMessage ? (
        <div className="error-state analysis-error" role="alert" data-testid={isTimeoutMessage(error) ? 'analysis-timeout' : 'analysis-error'}>
          <strong>{isTimeoutMessage(error) ? 'Analysis timed out.' : 'Analysis request failed.'}</strong>
          <p>{error}</p>
        </div>
      ) : null}

      {result ? <AnalysisResultView result={result} /> : null}
    </section>
  );
}

function isTimeoutMessage(message: string): boolean {
  return message.toLowerCase().includes('timed out') || message.toLowerCase().includes('timeout');
}

function AnalysisResultView({ result }: { result: AnalysisResult }) {
  return (
    <div className="analysis-result" data-testid="analysis-result">
      <div className="analysis-result-summary">
        <div>
          <span className="indicator-label">Engine</span>
          <strong>{result.engine.displayName}</strong>
          <small>{result.source.source}</small>
        </div>
        <div>
          <span className="indicator-label">Window</span>
          <strong>{formatBacktestWindow(result)}</strong>
          <small>{result.timeframe}</small>
        </div>
        <div>
          <span className="indicator-label">Result</span>
          <strong>{result.status}</strong>
          <small>{new Date(result.generatedAtUtc).toLocaleString()}</small>
        </div>
      </div>

      {result.backtest ? (
        <div className="analysis-metrics" data-testid="analysis-backtest-summary">
          <Metric label="Total return" value={`${result.backtest.totalReturnPercent.toFixed(2)}%`} />
          <Metric label="Final equity" value={formatCurrency(result.backtest.finalEquity)} />
          <Metric label="Signals" value={String(result.backtest.tradeCount)} />
          <Metric label="Win rate" value={`${result.backtest.winRatePercent.toFixed(1)}%`} />
        </div>
      ) : null}

      {result.metrics.length > 0 ? (
        <div className="analysis-metric-list">
          <h3>Metrics</h3>
          <ul>
            {result.metrics.map((metric) => (
              <li key={`${metric.name}-${metric.unit ?? 'value'}`}>
                <span>{formatMetricName(metric)}</span>
                <strong>{formatMetricValue(metric)}</strong>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="analysis-signals">
        <h3>Signals</h3>
        {result.signals.length === 0 ? <p>No analysis signals were generated for this window.</p> : null}
        <ul>
          {result.signals.map((signal) => (
            <li key={`${signal.time}-${signal.kind}-${signal.direction}`} data-testid="analysis-signal">
              <strong>{signal.direction}</strong>
              <span>{signal.kind}</span>
              <small>{new Date(signal.time).toLocaleString()} · confidence {(signal.confidence * 100).toFixed(0)}%</small>
              <p>{signal.rationale}</p>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="indicator-label">{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function formatSourceLabel(source: string | null | undefined): string {
  if (!source) {
    return 'the market-data provider';
  }

  return source.includes('ibkr') ? 'IBKR/iBeam' : source;
}

function formatBacktestWindow(result: AnalysisResult): string {
  if (!result.backtest) {
    return 'n/a';
  }

  return `${new Date(result.backtest.startUtc).toLocaleDateString()} → ${new Date(result.backtest.endUtc).toLocaleDateString()}`;
}

function formatMetricName(metric: AnalysisMetric): string {
  return metric.name.replaceAll('-', ' ');
}

function formatMetricValue(metric: AnalysisMetric): string {
  if (metric.unit === 'percent') {
    return `${metric.value.toFixed(2)}%`;
  }

  if (metric.unit === 'count') {
    return String(Math.round(metric.value));
  }

  return metric.unit ? `${metric.value.toFixed(4)} ${metric.unit}` : metric.value.toFixed(4);
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value);
}
