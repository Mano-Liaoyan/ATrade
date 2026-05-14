import { getDisabledTerminalModules, getEnabledTerminalModules } from "@/lib/terminalModuleRegistry";
import { TerminalPanel } from "./TerminalPanel";
import { TerminalStatusBadge } from "./TerminalStatusBadge";

export function TerminalHelpModule() {
  const enabledModules = getEnabledTerminalModules();
  const disabledModules = getDisabledTerminalModules();

  return (
    <section className="terminal-help-module terminal-module-scroll-surface" data-scroll-owner="help-module" data-testid="terminal-help-module" id="terminal-help" tabIndex={-1}>
      <TerminalPanel
        eyebrow="Workspace help"
        title="Module and workflow reference"
        description="Use the module rail and workflow actions."
        actions={<TerminalStatusBadge tone="info">HELP</TerminalStatusBadge>}
      >
        <p className="terminal-help-module__summary">Enabled modules open API-backed workflows. Disabled modules show unavailable labels.</p>
        <div className="terminal-help-module__grid">
          <div>
            <h3>Enabled modules</h3>
            <ul className="terminal-help-module__list">
              {enabledModules.map((module) => (
                <li key={module.id}>
                  <strong>{module.id}</strong>
                  <span>{module.description}</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3>Workflow actions</h3>
            <ul className="terminal-help-module__list">
              <li>
                <strong>Market monitor</strong>
                <span>Open chart, analysis, or backtest from rows.</span>
              </li>
              <li>
                <strong>Chart and analysis</strong>
                <span>Symbol routes preserve Exact Instrument Identity when available.</span>
              </li>
              <li>
                <strong>Status</strong>
                <span>Provider diagnostics show concise unavailable-state labels.</span>
              </li>
            </ul>
          </div>
          <div>
            <h3>Visible-disabled modules</h3>
            <ul className="terminal-help-module__list">
              {disabledModules.map((module) => (
                <li key={module.id}>
                  <strong>{module.id}</strong>
                  <span>{module.disabledMessage}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </TerminalPanel>

      <TerminalPanel
        className="terminal-help-module__safety"
        eyebrow="Safety"
        title="Paper-only and provider-boundary reminders"
        tone="inset"
        actions={<TerminalStatusBadge tone="warning">No orders</TerminalStatusBadge>}
      >
        <ul className="terminal-help-module__list">
          <li>Data is served by ATrade.Api.</li>
          <li>Visible labels include provider-not-configured, provider-unavailable, authentication-required, rate-limited, storage failures, analysis-engine-not-configured, analysis-engine-unavailable, empty candles, disabled module, and fallback.</li>
          <li>Orders are disabled. No order tickets or submit actions.</li>
        </ul>
      </TerminalPanel>
    </section>
  );
}
