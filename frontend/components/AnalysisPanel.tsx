'use client';

import type { InstrumentIdentityInput } from '../lib/instrumentIdentity';
import { useTerminalAnalysisWorkflow } from '../lib/terminalAnalysisWorkflow';
import type { AnalysisMetric, AnalysisResult } from '../types/analysis';
import type { ChartRange } from '../types/marketData';

type AnalysisPanelProps = {
  symbol: string;
  chartRange: ChartRange;
  candleSource?: string | null;
  identity?: InstrumentIdentityInput | null;
};

export function AnalysisPanel({ symbol, chartRange, candleSource, identity = null }: AnalysisPanelProps) {
  const analysis = useTerminalAnalysisWorkflow({ symbol, chartRange, candleSource, identity });

  return (
    <section className="analysis-panel" data-testid="analysis-panel" aria-live="polite">
      <div className="panel-heading analysis-heading">
        <div>
          <p className="eyebrow">Analysis engine</p>
          <h2>Provider-neutral signals</h2>
        </div>
        <span className={analysis.runnableEngine ? 'pill analysis-pill--ready' : 'pill analysis-pill--muted'} data-testid="analysis-engine-state">
          {analysis.engineStateLabel}
        </span>
      </div>

      <p className="analysis-copy">
        Run an analysis-only backtest over the current {analysis.chartRangeLabel} lookback candles ({analysis.chartRangeDescription.toLowerCase()}) from {analysis.sourceLabel}. Results are signals and metrics only;
        this panel never places orders or starts automated trading. {analysis.providerNeutralCopy}
      </p>

      {analysis.unavailableMessage ? (
        <div className="analysis-unavailable" data-testid="analysis-unavailable" role="status">
          <strong>Analysis unavailable.</strong>
          <p>{analysis.unavailableMessage}</p>
        </div>
      ) : null}

      <div className="analysis-actions">
        <button
          className="primary-button"
          type="button"
          data-testid="analysis-run-button"
          disabled={!analysis.canRun}
          onClick={() => void analysis.runAnalysis()}
        >
          {analysis.running ? 'Running analysis…' : `Run ${analysis.runnableEngine?.metadata.provider ?? 'analysis'}`}
        </button>
        <span data-testid="analysis-no-automation-note">{analysis.noOrderCopy}</span>
      </div>

      {analysis.running ? <div className="loading-state" role="status">Waiting for the configured analysis runtime…</div> : null}
      {analysis.error && !analysis.unavailableMessage ? (
        <div className="error-state analysis-error" role="alert" data-testid={isTimeoutMessage(analysis.error) ? 'analysis-timeout' : 'analysis-error'}>
          <strong>{isTimeoutMessage(analysis.error) ? 'Analysis timed out.' : 'Analysis request failed.'}</strong>
          <p>{analysis.error}</p>
        </div>
      ) : null}

      {analysis.result ? <AnalysisResultView result={analysis.result} /> : null}
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
