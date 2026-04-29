'use client';

import { useEffect, useState } from 'react';
import { getBrokerStatus } from '../lib/brokerStatusClient';
import type { BrokerStatus } from '../types/brokerStatus';

export function BrokerPaperStatus() {
  const [status, setStatus] = useState<BrokerStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadStatus() {
      try {
        const response = await getBrokerStatus();
        if (active) {
          setStatus(response);
          setError(null);
        }
      } catch (caughtError) {
        if (active) {
          setError(caughtError instanceof Error ? caughtError.message : 'Broker status unavailable.');
        }
      }
    }

    void loadStatus();
    const intervalId = window.setInterval(() => void loadStatus(), 30_000);

    return () => {
      active = false;
      window.clearInterval(intervalId);
    };
  }, []);

  return (
    <section className="workspace-panel broker-status-panel" data-testid="broker-paper-status">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">IBKR paper-mode status</p>
          <h2>Simulation guardrails</h2>
        </div>
        <span className="pill">No real orders</span>
      </div>

      {error ? <p className="error-text">Broker status unavailable: {error}</p> : null}
      {!error && !status ? <p>Loading paper broker status…</p> : null}
      {status ? (
        <dl className="broker-status-grid">
          <div>
            <dt>State</dt>
            <dd>{status.state}</dd>
          </div>
          <div>
            <dt>Mode</dt>
            <dd>{status.mode}</dd>
          </div>
          <div>
            <dt>Order placement</dt>
            <dd>{status.capabilities.supportsBrokerOrderPlacement ? 'enabled' : 'disabled'}</dd>
          </div>
        </dl>
      ) : null}

      <p className="safety-note">
        This frontend shows charting and status only. It does not submit live broker orders; any future order affordance must be labeled simulation-only and call the safe simulation endpoint.
      </p>
    </section>
  );
}
