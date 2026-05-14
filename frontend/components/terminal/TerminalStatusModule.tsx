import { TerminalMetadataGrid } from "./TerminalMetadataGrid";
import { TerminalPanel } from "./TerminalPanel";
import { TerminalStatusBadge } from "./TerminalStatusBadge";
import { TerminalProviderDiagnostics } from "./TerminalProviderDiagnostics";

export function TerminalStatusModule() {
  return (
    <section className="terminal-status-module terminal-module-scroll-surface workspace-stack" data-scroll-owner="status-module" data-testid="terminal-status-module" id="terminal-status" tabIndex={-1}>
      <TerminalPanel
        eyebrow="Operational status"
        title="Provider and workspace status"
        description="Concise operational labels for providers, cache, analysis, and fallback."
        actions={<TerminalStatusBadge tone="success">Paper only</TerminalStatusBadge>}
      >
        <TerminalMetadataGrid
          ariaLabel="Operational status metadata"
          className="terminal-status-module__grid"
          columns="auto"
          items={[
            {
              label: 'Frontend data boundary',
              value: 'ATrade.Api only.',
            },
            {
              label: 'Market data states',
              value: 'provider-not-configured, provider-unavailable, authentication-required, rate-limited, empty candles, storage failures.',
            },
            {
              label: 'Analysis runtime',
              value: 'analysis-engine-not-configured, analysis-engine-unavailable.',
            },
            {
              label: 'Order controls',
              value: 'Disabled module. No order controls.',
            },
          ]}
        />
      </TerminalPanel>
      <TerminalProviderDiagnostics />
    </section>
  );
}
