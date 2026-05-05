'use client';

import type { InstrumentIdentityInput } from '@/lib/instrumentIdentity';
import { useTerminalAnalysisWorkflow } from '@/lib/terminalAnalysisWorkflow';
import { cn } from '@/lib/utils';
import type { AnalysisMetric, AnalysisResult } from '@/types/analysis';
import { type ChartRange } from '@/types/marketData';
import { Button } from '../ui/button';
import { TerminalPanel } from './TerminalPanel';
import { TerminalStatusBadge, type TerminalStatusTone } from './TerminalStatusBadge';

export type TerminalAnalysisWorkspaceProps = {
  chartRange?: ChartRange;
  className?: string;
  candleSource?: string | null;
  identity?: InstrumentIdentityInput | null;
  symbol: string | null;
};

export function TerminalAnalysisWorkspace({
  chartRange = '1D',
  className,
  candleSource = null,
  identity = null,
  symbol,
}: TerminalAnalysisWorkspaceProps) {
  if (!symbol) {
    return <TerminalAnalysisPlaceholder className={className} />;
  }

  return (
    <TerminalAnalysisWorkspaceContent
      chartRange={chartRange}
      className={className}
      candleSource={candleSource}
      identity={identity}
      symbol={symbol}
    />
  );
}

type TerminalAnalysisWorkspaceContentProps = {
  chartRange: ChartRange;
  className?: string;
  candleSource: string | null;
  identity?: InstrumentIdentityInput | null;
  symbol: string;
};

function TerminalAnalysisWorkspaceContent({
  chartRange,
  className,
  candleSource,
  identity,
  symbol,
}: TerminalAnalysisWorkspaceContentProps) {
  const analysis = useTerminalAnalysisWorkflow({ symbol, chartRange, candleSource, identity });
  const stateTone = getAnalysisStateTone(analysis.engineState);

  return (
    <section className={cn('terminal-analysis-workspace', className)} data-testid="terminal-analysis-workspace" aria-live="polite">
      <TerminalPanel
        className="terminal-analysis-workspace__header"
        data-testid="analysis-panel"
        density="compact"
        eyebrow="Analysis"
        title={`${analysis.symbol} provider-neutral analysis`}
        description="Discovery and runs stay behind ATrade.Api analysis contracts with explicit no-engine and runtime-unavailable states."
        actions={(
          <div className="terminal-analysis-workspace__badges">
            <TerminalStatusBadge tone={stateTone} pulse={analysis.engineState === 'checking' || analysis.engineState === 'running'} data-testid="terminal-analysis-engine-state">
              {analysis.engineStateLabel}
            </TerminalStatusBadge>
            <TerminalStatusBadge tone="warning">No orders</TerminalStatusBadge>
          </div>
        )}
      >
        <div className="terminal-analysis-workspace__summary">
          <div>
            <span>Lookback</span>
            <strong>{analysis.chartRangeLabel}</strong>
            <small>{analysis.chartRangeDescription}</small>
          </div>
          <div>
            <span>Candle source</span>
            <strong>{analysis.sourceLabel}</strong>
            <small>{analysis.requestIdentity ? `${analysis.requestIdentity.provider.toUpperCase()} ${analysis.requestIdentity.providerSymbolId ?? analysis.requestIdentity.symbol}` : 'Symbol-only request'}</small>
          </div>
          <div>
            <span>Safety</span>
            <strong>Analysis only</strong>
            <small data-testid="analysis-no-automation-note">{analysis.noOrderCopy}</small>
          </div>
        </div>

        <p className="terminal-analysis-workspace__copy">
          {analysis.providerNeutralCopy} Results are signals, metrics, and optional backtest summaries only; no brokerage routing, live trading, or automated order placement is exposed.
        </p>

        {analysis.unavailableMessage ? (
          <div className="terminal-analysis-workspace__unavailable" data-testid="analysis-unavailable" role="status">
            <strong>{analysis.engineState === 'not-configured' ? 'No analysis engine configured.' : 'Analysis unavailable.'}</strong>
            <p>{analysis.unavailableMessage}</p>
          </div>
        ) : null}

        <div className="terminal-analysis-workspace__actions">
          <Button data-testid="analysis-run-button" disabled={!analysis.canRun} onClick={() => void analysis.runAnalysis()} size="sm" type="button" variant="terminal">
            {analysis.running ? 'Running analysis…' : `Run ${analysis.runnableEngine?.metadata.provider ?? 'analysis'}`}
          </Button>
          <span>{analysis.noOrderCopy}</span>
        </div>

        {analysis.running ? <div className="loading-state" role="status">Waiting for the configured analysis runtime…</div> : null}
        {analysis.error && !analysis.unavailableMessage ? (
          <div className="error-state analysis-error" role="alert" data-testid={isTimeoutMessage(analysis.error) ? 'analysis-timeout' : 'analysis-error'}>
            <strong>{isTimeoutMessage(analysis.error) ? 'Analysis timed out.' : 'Analysis request failed.'}</strong>
            <p>{analysis.error}</p>
          </div>
        ) : null}

        {analysis.result ? <TerminalAnalysisResultView result={analysis.result} /> : null}
      </TerminalPanel>
    </section>
  );
}

function TerminalAnalysisPlaceholder({ className }: { className?: string }) {
  return (
    <section className={cn('terminal-analysis-workspace', className)} data-testid="terminal-analysis-workspace" aria-live="polite">
      <TerminalPanel
        density="compact"
        eyebrow="Analysis"
        title="Open analysis for a symbol"
        description="Select analysis from a chart or market monitor row. Engine discovery remains provider-neutral and no fake signals are shown."
        actions={<TerminalStatusBadge tone="info">ANALYSIS</TerminalStatusBadge>}
      >
        <div className="terminal-analysis-workspace__unavailable" data-testid="analysis-unavailable" role="status">
          <strong>No symbol selected.</strong>
          <p>Choose a chartable instrument before running provider-neutral analysis. No analysis engine or result is fabricated for the empty state.</p>
        </div>
        <p data-testid="analysis-no-automation-note">Analysis only — no brokerage routing or automatic order placement.</p>
      </TerminalPanel>
    </section>
  );
}

function TerminalAnalysisResultView({ result }: { result: AnalysisResult }) {
  return (
    <div className="terminal-analysis-result" data-testid="analysis-result">
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

function getAnalysisStateTone(state: string): TerminalStatusTone {
  switch (state) {
    case 'ready':
      return 'success';
    case 'checking':
    case 'running':
      return 'info';
    case 'failed':
    case 'unavailable':
      return 'danger';
    case 'not-configured':
      return 'warning';
    default:
      return 'neutral';
  }
}

function isTimeoutMessage(message: string): boolean {
  return message.toLowerCase().includes('timed out') || message.toLowerCase().includes('timeout');
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
