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
  analysisStateLabel = 'Provider-neutral analysis discovery through ATrade.Api',
  marketDataSourceLabel = 'Market-data source labels are surfaced on chart and monitor payloads',
  signalRStateLabel = 'SignalR state is reported inside active chart workspaces',
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
        title="IBKR, iBeam, data source, and analysis runtime states"
        description="Diagnostics surface provider readiness and source labels without credential fields, account identifiers, order tickets, or broker-routing controls."
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
      detail: status?.message ?? 'Safe broker readiness projection from ATrade.Api.',
      label: 'Broker provider',
      value: status?.provider ?? 'ibkr',
    },
    {
      detail: `Connected ${formatBoolean(status?.connected)} · authenticated ${formatBoolean(status?.authenticated)} · competing ${formatBoolean(status?.competing)}`,
      label: 'IBKR/iBeam state',
      value: status?.state ?? (error ? 'unavailable' : 'checking'),
    },
    {
      detail: 'Paper-only status is shown without account identifiers or credential prompts.',
      label: 'Paper mode',
      value: status?.mode ?? 'paper',
    },
    {
      detail: 'Chart, monitor, candles, indicators, and Timescale cache labels remain payload-owned.',
      label: 'Market data source',
      value: marketDataSourceLabel,
    },
    {
      detail: 'HTTP polling fallback remains visible when stream state is closed or unavailable.',
      label: 'SignalR stream',
      value: signalRStateLabel,
    },
    {
      detail: 'No-engine and runtime-unavailable states are explicit; no fake signals are generated.',
      label: 'Analysis provider',
      value: analysisStateLabel,
    },
    {
      detail: 'Diagnostics only — the workspace renders no order-entry controls and does not call broker order routes.',
      label: 'Order placement capability',
      value: status?.capabilities.supportsBrokerOrderPlacement ? 'provider reports enabled' : 'disabled',
    },
    {
      detail: 'Secrets, account identifiers, tokens, cookies, gateway URLs, and session values stay out of the browser UI.',
      label: 'Credential UI',
      value: 'not rendered',
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
