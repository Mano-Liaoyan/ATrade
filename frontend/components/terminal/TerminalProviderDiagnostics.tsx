'use client';

import { useEffect, useState } from 'react';

import { getBrokerStatus } from '@/lib/brokerStatusClient';
import type { BrokerStatus } from '@/types/brokerStatus';
import { Button } from '../ui/button';
import { TerminalMetadataGrid, type TerminalMetadataItem } from './TerminalMetadataGrid';
import { TerminalPanel } from './TerminalPanel';
import { TerminalStatusBadge, type TerminalStatusTone } from './TerminalStatusBadge';

export type TerminalProviderDiagnosticsProps = {
  analysisStateLabel?: string;
  marketDataSourceLabel?: string;
  signalRStateLabel?: string;
};

export function TerminalProviderDiagnostics({
  analysisStateLabel = 'analysis state pending',
  marketDataSourceLabel = 'market-data source pending',
  signalRStateLabel = 'fallback status pending',
}: TerminalProviderDiagnosticsProps) {
  const [status, setStatus] = useState<BrokerStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadStatus() {
    setLoading(true);

    try {
      const response = await getBrokerStatus();
      setStatus(response);
      setError(null);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Broker provider diagnostics are unavailable.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let active = true;

    async function loadInitialStatus() {
      setLoading(true);

      try {
        const response = await getBrokerStatus();
        if (active) {
          setStatus(response);
          setError(null);
        }
      } catch (caughtError) {
        if (active) {
          setError(caughtError instanceof Error ? caughtError.message : 'Broker provider diagnostics are unavailable.');
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadInitialStatus();
    const intervalId = window.setInterval(() => void loadInitialStatus(), 30_000);

    return () => {
      active = false;
      window.clearInterval(intervalId);
    };
  }, []);

  const brokerTone = getBrokerTone(status, error, loading);

  return (
    <section className="terminal-provider-diagnostics" data-testid="terminal-provider-diagnostics">
      <TerminalPanel
        density="compact"
        eyebrow="Provider diagnostics"
        title="Provider diagnostics"
        description="Readiness, source, fallback, and analysis labels."
        actions={(
          <div className="terminal-provider-diagnostics__actions">
            <TerminalStatusBadge tone={brokerTone} pulse={loading}>{loading ? 'Checking' : error ? 'Unavailable' : status?.state ?? 'Unknown'}</TerminalStatusBadge>
            <Button onClick={() => void loadStatus()} size="xs" type="button" variant="outline">Refresh diagnostics</Button>
          </div>
        )}
      >
        {error ? <p className="error-text" role="alert">Broker diagnostics unavailable: {error}</p> : null}
        {!error && loading && !status ? <p role="status">Loading broker provider diagnostics…</p> : null}

        <TerminalMetadataGrid
          ariaLabel="Provider diagnostics metadata"
          className="terminal-provider-diagnostics__grid"
          columns={3}
          items={getDiagnosticItems({ analysisStateLabel, marketDataSourceLabel, signalRStateLabel, status, error })}
        />
      </TerminalPanel>
    </section>
  );
}

function getDiagnosticItems({
  analysisStateLabel,
  error,
  marketDataSourceLabel,
  signalRStateLabel,
  status,
}: {
  analysisStateLabel: string;
  error: string | null;
  marketDataSourceLabel: string;
  signalRStateLabel: string;
  status: BrokerStatus | null;
}): TerminalMetadataItem[] {
  return [
    {
      detail: status?.message ?? 'Provider status pending.',
      label: 'Broker provider',
      value: status?.provider ?? 'ibkr',
    },
    {
      detail: `Connected ${formatBoolean(status?.connected)} · authenticated ${formatBoolean(status?.authenticated)} · competing ${formatBoolean(status?.competing)}`,
      label: 'IBKR/iBeam state',
      value: status?.state ?? (error ? 'unavailable' : 'checking'),
    },
    {
      detail: 'Paper mode only.',
      label: 'Paper mode',
      value: status?.mode ?? 'paper',
    },
    {
      detail: 'Source and cache labels stay with chart and monitor data.',
      label: 'Market data source',
      value: marketDataSourceLabel,
    },
    {
      detail: 'SignalR-to-HTTP fallback status stays visible.',
      label: 'Workspace stream',
      value: signalRStateLabel,
    },
    {
      detail: 'analysis-engine-not-configured and analysis-engine-unavailable stay explicit.',
      label: 'Analysis provider',
      value: analysisStateLabel,
    },
    {
      detail: 'No order controls.',
      label: 'Order placement capability',
      value: status?.capabilities.supportsBrokerOrderPlacement ? 'provider reports enabled' : 'disabled',
    },
    {
      detail: 'Sensitive values are not shown.',
      label: 'Sensitive UI',
      value: 'not shown',
    },
  ];
}

function getBrokerTone(status: BrokerStatus | null, error: string | null, loading: boolean): TerminalStatusTone {
  if (loading) {
    return 'info';
  }

  if (error) {
    return 'danger';
  }

  if (status?.connected && status.authenticated) {
    return 'success';
  }

  if (status?.state === 'disabled' || status?.state === 'not-configured') {
    return 'warning';
  }

  return 'neutral';
}

function formatBoolean(value: boolean | undefined): string {
  return value === undefined ? 'unknown' : value ? 'yes' : 'no';
}
