'use client';

import { useEffect, useMemo, useState } from 'react';

import {
  checkWorkspaceHttpReadState,
  connectWorkspaceStatusStream,
  createInitialWorkspaceStatusState,
  projectWorkspaceSignalRStatus,
  type WorkspaceStatusState,
} from '@/lib/workspaceStatusClient';
import { TerminalStatusBadge } from './TerminalStatusBadge';

export function TerminalWorkspaceStatusIndicator() {
  const [status, setStatus] = useState<WorkspaceStatusState>(() => createInitialWorkspaceStatusState());
  const projection = useMemo(() => projectWorkspaceSignalRStatus(status), [status]);

  useEffect(() => {
    let active = true;
    let stopStream: (() => Promise<void>) | null = null;

    connectWorkspaceStatusStream({
      onStateChange: (signalRState) => {
        if (active) {
          setStatus((current) => ({ ...current, signalRState }));
        }
      },
    }).then((subscription) => {
      if (!active) {
        void subscription.stop();
        return;
      }

      stopStream = subscription.stop;
    }).catch(() => {
      if (active) {
        setStatus((current) => ({ ...current, signalRState: 'unavailable' }));
      }
    });

    return () => {
      active = false;
      if (stopStream) {
        void stopStream();
      }
    };
  }, []);

  useEffect(() => {
    let active = true;

    async function refreshHttpReadState() {
      setStatus((current) => ({ ...current, httpReadState: current.httpReadState === 'unchecked' ? 'checking' : current.httpReadState }));
      const httpReadState = await checkWorkspaceHttpReadState();
      if (active) {
        setStatus((current) => ({ ...current, httpReadState }));
      }
    }

    void refreshHttpReadState();
    const intervalId = window.setInterval(() => void refreshHttpReadState(), 30_000);

    return () => {
      active = false;
      window.clearInterval(intervalId);
    };
  }, []);

  return (
    <div
      aria-live="polite"
      className="terminal-workspace-status-indicator"
      data-status-state={projection.id}
      data-testid="terminal-global-signalr-status"
      role="status"
      title={projection.detail}
    >
      <TerminalStatusBadge tone={projection.tone} pulse={projection.pulse}>SignalR {projection.label}</TerminalStatusBadge>
      <span className="terminal-workspace-status-indicator__detail">{projection.detail}</span>
    </div>
  );
}
