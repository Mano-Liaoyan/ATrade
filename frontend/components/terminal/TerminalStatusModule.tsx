import { TerminalPanel } from "./TerminalPanel";
import { TerminalStatusBadge } from "./TerminalStatusBadge";
import { TerminalProviderDiagnostics } from "./TerminalProviderDiagnostics";

export function TerminalStatusModule() {
  return (
    <section className="terminal-status-module workspace-stack" data-testid="terminal-status-module" id="terminal-status" tabIndex={-1}>
      <TerminalPanel
        eyebrow="Operational status"
        title="ATrade.Api, provider, and paper-mode boundary"
        description="The workspace keeps runtime status visible while preserving explicit unavailable states and browser/API separation."
        actions={<TerminalStatusBadge tone="success">Paper only</TerminalStatusBadge>}
      >
        <dl className="terminal-status-module__grid">
          <div>
            <dt>Frontend data boundary</dt>
            <dd>Browser routes through ATrade.Api only.</dd>
          </div>
          <div>
            <dt>Market data truth</dt>
            <dd>IBKR/iBeam or Timescale cache states remain visible; no synthetic fallback data is injected.</dd>
          </div>
          <div>
            <dt>Analysis runtime</dt>
            <dd>Provider-neutral analysis reports no-engine or runtime-unavailable states honestly.</dd>
          </div>
          <div>
            <dt>Order controls</dt>
            <dd>Disabled in this paper workspace.</dd>
          </div>
        </dl>
      </TerminalPanel>
      <TerminalProviderDiagnostics />
    </section>
  );
}
