'use client';

import type { InstrumentIdentityInput } from '@/lib/instrumentIdentity';
import {
  formatBacktestCapitalSource,
  formatBacktestStatusLabel,
  useTerminalBacktestWorkflow,
  type TerminalBacktestWorkflow,
} from '@/lib/terminalBacktestWorkflow';
import { cn } from '@/lib/utils';
import { SUPPORTED_CHART_RANGES, type ChartRange } from '@/types/marketData';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { TerminalPanel } from './TerminalPanel';
import type { BacktestRunEnvelope } from '@/types/backtesting';
import { TerminalStatusBadge, type TerminalStatusTone } from './TerminalStatusBadge';

export type TerminalBacktestWorkspaceProps = {
  chartRange?: ChartRange;
  className?: string;
  identity?: InstrumentIdentityInput | null;
  symbol?: string | null;
};

export function TerminalBacktestWorkspace({
  chartRange = '1D',
  className,
  identity = null,
  symbol = null,
}: TerminalBacktestWorkspaceProps) {
  const workflow = useTerminalBacktestWorkflow({
    initialChartRange: chartRange,
    initialIdentity: identity,
    initialSymbol: symbol,
  });

  return (
    <section className={cn('terminal-backtest-workspace workspace-stack', className)} data-testid="terminal-backtest-workspace" aria-live="polite">
      <TerminalPanel
        className="terminal-backtest-workspace__header"
        data-testid="backtest-run-form-panel"
        density="compact"
        eyebrow="Backtest"
        title={workflow.normalizedSymbol ? `${workflow.normalizedSymbol} saved backtest` : 'Saved backtest run'}
        description="Create one provider-neutral, single-symbol strategy run through ATrade.Api saved backtest contracts."
        actions={(
          <div className="terminal-backtest-workspace__badges">
            <TerminalStatusBadge tone={workflow.streamState === 'connected' ? 'success' : workflow.streamState === 'unavailable' ? 'warning' : 'info'} pulse={workflow.streamState === 'connecting' || workflow.streamState === 'reconnecting'} data-testid="backtest-stream-state">
              SignalR {workflow.streamState}
            </TerminalStatusBadge>
            <TerminalStatusBadge tone="warning">No orders</TerminalStatusBadge>
          </div>
        )}
      >
        <div className="terminal-backtest-workspace__summary">
          <div>
            <span>Instrument</span>
            <strong>{workflow.normalizedSymbol || 'None selected'}</strong>
            <small>{workflow.identitySummary}</small>
          </div>
          <div>
            <span>Capital source</span>
            <strong>{workflow.capital ? formatBacktestCapitalSource(workflow.capital.source) : workflow.capitalLoading ? 'Loading…' : 'Unavailable'}</strong>
            <small>{workflow.capitalCopy}</small>
          </div>
          <div>
            <span>Safety</span>
            <strong>Simulation only</strong>
            <small data-testid="backtest-no-order-note">{workflow.noOrderCopy}</small>
          </div>
        </div>

        <BacktestCapitalPanel workflow={workflow} />
        <BacktestRunForm workflow={workflow} />
        <BacktestLiveStatusPanel workflow={workflow} />
      </TerminalPanel>
    </section>
  );
}

function BacktestCapitalPanel({ workflow }: { workflow: TerminalBacktestWorkflow }) {
  const effectiveCapital = workflow.capital?.effectiveCapital ?? null;
  const capitalSource = workflow.capital ? formatBacktestCapitalSource(workflow.capital.source) : 'Unavailable';
  const sourceTone = workflow.capital?.source === 'unavailable' || workflow.capitalError ? 'warning' : 'success';

  return (
    <div className="terminal-backtest-capital" data-testid="backtest-capital-panel">
      <div className="terminal-backtest-capital__status">
        <div>
          <span>Effective paper capital</span>
          <strong>{effectiveCapital === null ? 'Unavailable' : formatCurrency(effectiveCapital, workflow.capital?.currency ?? workflow.capitalCurrency)}</strong>
          <small>{workflow.capitalLoading ? 'Loading effective capital from ATrade.Api…' : `${capitalSource} · ${workflow.capital?.currency ?? workflow.capitalCurrency}`}</small>
        </div>
        <TerminalStatusBadge tone={sourceTone} data-testid="backtest-capital-source">
          {capitalSource}
        </TerminalStatusBadge>
      </div>

      {workflow.capital?.ibkrAvailable ? (
        <div className="terminal-backtest-capital__sources" data-testid="backtest-capital-sources">
          <div>
            <span>IBKR paper source</span>
            <strong>{workflow.capital.ibkrAvailable.available ? 'Available' : workflow.capital.ibkrAvailable.state}</strong>
            <small>{workflow.capital.ibkrAvailable.available ? formatCurrency(workflow.capital.ibkrAvailable.capital ?? 0, workflow.capital.ibkrAvailable.currency) : 'No account identifiers are shown in the browser.'}</small>
          </div>
          <div>
            <span>Local paper capital</span>
            <strong>{workflow.capital.localConfigured ? formatCurrency(workflow.capital.localCapital ?? 0, workflow.capital.currency) : 'Not configured'}</strong>
            <small>Stored behind ATrade.Api /api/accounts/local-paper-capital.</small>
          </div>
        </div>
      ) : null}

      <form
        className="terminal-backtest-capital__form"
        data-testid="backtest-local-capital-form"
        onSubmit={(event) => {
          event.preventDefault();
          void workflow.updateCapital();
        }}
      >
        <label className="terminal-field">
          <span>Set local paper capital</span>
          <Input
            data-testid="backtest-local-capital-input"
            inputMode="decimal"
            min={0}
            onChange={(event) => workflow.setCapitalInput(event.target.value)}
            placeholder="100000"
            step="0.01"
            type="number"
            value={workflow.capitalInput}
          />
          <small>Used only when IBKR paper balance is unavailable; browser never receives IBKR account ids.</small>
        </label>
        <label className="terminal-field terminal-backtest-capital__currency">
          <span>Currency</span>
          <Input
            data-testid="backtest-local-capital-currency-input"
            maxLength={3}
            onChange={(event) => workflow.setCapitalCurrency(event.target.value.toUpperCase())}
            value={workflow.capitalCurrency}
          />
          <small>ISO currency code.</small>
        </label>
        <Button data-testid="backtest-update-capital-button" disabled={workflow.updatingCapital} size="sm" type="submit" variant="terminal">
          {workflow.updatingCapital ? 'Saving capital…' : 'Set local capital'}
        </Button>
      </form>

      {workflow.validation.fieldErrors.capital ? (
        <div className="terminal-backtest-workspace__alert" data-testid="backtest-capital-unavailable" role="status">
          {workflow.validation.fieldErrors.capital}
        </div>
      ) : null}
      {workflow.capital?.messages?.length ? (
        <ul className="terminal-backtest-capital__messages" aria-label="Paper capital messages">
          {workflow.capital.messages.map((message) => (
            <li key={`${message.code}-${message.message}`}>{message.message}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function BacktestLiveStatusPanel({ workflow }: { workflow: TerminalBacktestWorkflow }) {
  const run = workflow.selectedRun;
  const statusTone = getBacktestRunTone(run);
  const statusLabel = run ? formatBacktestStatusLabel(run.status) : 'No saved run';
  const explicitUnavailable = getExplicitUnavailableMessage(run) ?? workflow.streamError ?? workflow.historyError ?? workflow.detailError;

  return (
    <div className="terminal-backtest-live" data-testid="backtest-live-status-panel">
      <div className="terminal-backtest-live__header">
        <div>
          <span>Live run status</span>
          <strong>{run ? `${run.request.symbol.symbol} · ${run.request.strategyId}` : 'No run selected'}</strong>
          <small>{run ? getBacktestRunStatusCopy(run) : 'Create a run or select saved history. No demo run or placeholder result is shown.'}</small>
        </div>
        <TerminalStatusBadge tone={statusTone} pulse={run?.status === 'queued' || run?.status === 'running'} data-testid="backtest-selected-run-status">
          {statusLabel}
        </TerminalStatusBadge>
      </div>

      {run ? (
        <div className="terminal-backtest-live__grid">
          <div>
            <span>Created</span>
            <strong>{formatDateTime(run.createdAtUtc)}</strong>
            <small>Updated {formatDateTime(run.updatedAtUtc)}</small>
          </div>
          <div>
            <span>Capital</span>
            <strong>{formatCurrency(run.capital.initialCapital, run.capital.currency)}</strong>
            <small>{formatBacktestCapitalSource(run.capital.capitalSource)}</small>
          </div>
          <div>
            <span>Result</span>
            <strong>{run.result?.backtest ? `${run.result.backtest.totalReturnPercent.toFixed(2)}%` : 'Not available'}</strong>
            <small>{run.result ? 'Persisted completed result envelope.' : 'No fake result is rendered before completion.'}</small>
          </div>
        </div>
      ) : null}

      {explicitUnavailable ? (
        <div className="terminal-backtest-workspace__alert" data-testid="backtest-unavailable-state" role="status">
          {explicitUnavailable}
        </div>
      ) : null}

      {workflow.actionError ? (
        <div className="terminal-backtest-workspace__alert" data-testid="backtest-action-error" role="alert">
          {workflow.actionError}
        </div>
      ) : null}

      <div className="terminal-backtest-live__actions">
        <Button
          data-testid="backtest-cancel-run-button"
          disabled={!workflow.canCancelRun(run)}
          onClick={() => void workflow.cancelRun(run?.id)}
          size="sm"
          type="button"
          variant="destructive"
        >
          Cancel run
        </Button>
        <Button
          data-testid="backtest-retry-run-button"
          disabled={!workflow.canRetryRun(run)}
          onClick={() => void workflow.retryRun(run?.id)}
          size="sm"
          type="button"
          variant="terminal"
        >
          Retry as new run
        </Button>
        <Button data-testid="backtest-reload-status-button" onClick={() => void workflow.reloadSelectedRun()} size="sm" type="button" variant="ghost">
          Reload detail
        </Button>
        <span>{workflow.signalRCopy}</span>
      </div>
    </div>
  );
}

function BacktestRunForm({ workflow }: { workflow: TerminalBacktestWorkflow }) {
  const firstError = workflow.validation.errors[0] ?? workflow.actionError ?? workflow.capitalError;

  return (
    <form
      className="terminal-backtest-form"
      data-testid="backtest-run-form"
      onSubmit={(event) => {
        event.preventDefault();
        void workflow.createRun();
      }}
    >
      <div className="terminal-backtest-form__grid">
        <label className="terminal-field">
          <span>Single stock symbol</span>
          <Input
            aria-invalid={Boolean(workflow.validation.fieldErrors.symbol)}
            data-testid="backtest-symbol-input"
            maxLength={32}
            onChange={(event) => workflow.setSymbol(event.target.value)}
            placeholder="AAPL"
            value={workflow.symbol}
          />
          <small>{workflow.validation.fieldErrors.symbol ?? 'One symbol only; exact identity is preserved when opened from chart or market monitor.'}</small>
        </label>

        <label className="terminal-field">
          <span>Chart range</span>
          <select
            className="terminal-select"
            data-testid="backtest-chart-range-select"
            onChange={(event) => workflow.setChartRange(event.target.value as ChartRange)}
            value={workflow.chartRange}
          >
            {SUPPORTED_CHART_RANGES.map((range) => (
              <option key={range} value={range}>{range}</option>
            ))}
          </select>
          <small>{workflow.chartRangeDescription}</small>
        </label>

        <label className="terminal-field">
          <span>Strategy</span>
          <select
            className="terminal-select"
            data-testid="backtest-strategy-select"
            onChange={(event) => workflow.setStrategyId(event.target.value as typeof workflow.strategyId)}
            value={workflow.strategyId}
          >
            {workflow.strategies.map((strategy) => (
              <option key={strategy.id} value={strategy.id}>{strategy.displayName}</option>
            ))}
          </select>
          <small>{workflow.strategyDefinition.description}</small>
        </label>
      </div>

      <div className="terminal-backtest-form__parameters" data-testid="backtest-parameter-fields">
        {workflow.strategyDefinition.parameters.map((parameter) => {
          const fieldError = workflow.validation.fieldErrors[`parameter:${parameter.name}`];
          return (
            <label className="terminal-field" key={parameter.name}>
              <span>{parameter.displayName}</span>
              <Input
                aria-invalid={Boolean(fieldError)}
                data-testid={`backtest-parameter-${parameter.name}`}
                inputMode="decimal"
                min={parameter.minimumValue}
                max={parameter.maximumValue}
                onChange={(event) => workflow.setParameterValue(parameter.name, event.target.value)}
                step={parameter.valueType === 'integer' ? 1 : 0.01}
                type="number"
                value={workflow.parameterValues[parameter.name] ?? ''}
              />
              <small>{fieldError ?? parameter.description}</small>
            </label>
          );
        })}
      </div>

      <div className="terminal-backtest-form__costs" data-testid="backtest-cost-fields">
        <label className="terminal-field">
          <span>Commission / trade</span>
          <Input
            aria-invalid={Boolean(workflow.validation.fieldErrors.commissionPerTrade)}
            data-testid="backtest-commission-per-trade-input"
            inputMode="decimal"
            min={0}
            onChange={(event) => workflow.setCommissionPerTrade(event.target.value)}
            step="0.01"
            type="number"
            value={workflow.commissionPerTrade}
          />
          <small>{workflow.validation.fieldErrors.commissionPerTrade ?? 'Flat simulated commission per completed trade.'}</small>
        </label>
        <label className="terminal-field">
          <span>Commission bps</span>
          <Input
            aria-invalid={Boolean(workflow.validation.fieldErrors.commissionBps)}
            data-testid="backtest-commission-bps-input"
            inputMode="decimal"
            min={0}
            onChange={(event) => workflow.setCommissionBps(event.target.value)}
            step="0.01"
            type="number"
            value={workflow.commissionBps}
          />
          <small>{workflow.validation.fieldErrors.commissionBps ?? 'Basis-point simulated commission input.'}</small>
        </label>
        <label className="terminal-field">
          <span>Slippage bps</span>
          <Input
            aria-invalid={Boolean(workflow.validation.fieldErrors.slippageBps)}
            data-testid="backtest-slippage-bps-input"
            inputMode="decimal"
            min={0}
            onChange={(event) => workflow.setSlippageBps(event.target.value)}
            step="0.01"
            type="number"
            value={workflow.slippageBps}
          />
          <small>{workflow.validation.fieldErrors.slippageBps ?? 'Basis-point simulated slippage input.'}</small>
        </label>
        <label className="terminal-field">
          <span>Benchmark</span>
          <select
            className="terminal-select"
            data-testid="backtest-benchmark-select"
            onChange={(event) => workflow.setBenchmarkMode(event.target.value as typeof workflow.benchmarkMode)}
            value={workflow.benchmarkMode}
          >
            <option value="buy-and-hold">Buy and hold</option>
            <option value="none">None</option>
          </select>
          <small>Optional buy-and-hold benchmark result envelope.</small>
        </label>
      </div>

      {firstError ? (
        <div className="terminal-backtest-workspace__alert" data-testid="backtest-form-error" role="alert">
          {firstError}
        </div>
      ) : null}

      <div className="terminal-backtest-form__actions">
        <Button data-testid="backtest-create-run-button" disabled={!workflow.canCreateRun} type="submit" variant="amber">
          {workflow.creatingRun ? 'Creating run…' : 'Create backtest run'}
        </Button>
        <span>{workflow.signalRCopy}</span>
      </div>
    </form>
  );
}

function getBacktestRunTone(run: BacktestRunEnvelope | null): TerminalStatusTone {
  if (!run) {
    return 'neutral';
  }

  switch (run.status) {
    case 'queued':
    case 'running':
      return 'info';
    case 'completed':
      return 'success';
    case 'failed':
      return 'danger';
    case 'cancelled':
      return 'warning';
    default:
      return 'neutral';
  }
}

function getBacktestRunStatusCopy(run: BacktestRunEnvelope): string {
  switch (run.status) {
    case 'queued':
      return 'Queued by ATrade.Api and waiting for the async runner.';
    case 'running':
      return 'Running server-side through market-data and analysis seams.';
    case 'completed':
      return run.result ? 'Completed with a saved result envelope.' : 'Completed without a result payload from the backend.';
    case 'failed':
      return run.error?.message ?? 'The run failed with a saved backend error.';
    case 'cancelled':
      return 'Cancelled best-effort; retry creates a new saved run.';
    default:
      return `Backend status: ${run.status}`;
  }
}

function getExplicitUnavailableMessage(run: BacktestRunEnvelope | null): string | null {
  if (!run?.error) {
    return null;
  }

  if (run.error.code === 'backtest-analysis-unavailable') {
    return `Analysis engine unavailable: ${run.error.message}`;
  }

  if (run.error.code === 'backtest-market-data-unavailable') {
    return `Market-data provider unavailable: ${run.error.message}`;
  }

  if (run.error.code === 'backtest-runner-unavailable') {
    return `Backtest runner unavailable: ${run.error.message}`;
  }

  return run.status === 'failed' ? run.error.message : null;
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return 'n/a';
  }

  return new Date(value).toLocaleString();
}

function formatCurrency(value: number, currency = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(value);
}
