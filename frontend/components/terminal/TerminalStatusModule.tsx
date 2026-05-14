import { TerminalMetadataGrid } from "./TerminalMetadataGrid";
import { TerminalPanel } from "./TerminalPanel";
import { TerminalStatusBadge } from "./TerminalStatusBadge";
import { TerminalProviderDiagnostics } from "./TerminalProviderDiagnostics";

export function TerminalStatusModule() {
  return (
    <section className="terminal-status-module terminal-module-scroll-surface workspace-stack" data-scroll-owner="status-module" data-testid="terminal-status-module" id="terminal-status" tabIndex={-1}>
      <TerminalPanel
        eyebrow="Operational status"
        title="ATrade.Api, provider, and paper-mode boundary"
        description="The workspace keeps runtime status visible while preserving explicit unavailable states and browser/API separation."
        actions={<TerminalStatusBadge tone="success">Paper only</TerminalStatusBadge>}
      >
        <TerminalMetadataGrid
          ariaLabel="Operational status metadata"
          className="terminal-status-module__grid"
          columns="auto"
          items={[
            {
              label: 'Frontend data boundary',
              value: 'Browser routes through ATrade.Api only.',
            },
            {
              label: 'Market data truth',
              value: 'IBKR/iBeam or Timescale cache states remain visible; no synthetic fallback data is injected.',
            },
            {
              label: 'Analysis runtime',
              value: 'Provider-neutral analysis reports no-engine or runtime-unavailable states honestly.',
            },
            {
              label: 'Order controls',
              value: 'Disabled in this paper workspace.',
            },
          ]}
        />
      </TerminalPanel>
      <TerminalProviderDiagnostics />
    </section>
  );
}
