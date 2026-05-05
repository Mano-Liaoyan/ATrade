import { getDisabledTerminalModules, getEnabledTerminalModules } from "@/lib/terminalModuleRegistry";
import { TerminalPanel } from "./TerminalPanel";
import { TerminalStatusBadge } from "./TerminalStatusBadge";

export function TerminalHelpModule() {
  const enabledModules = getEnabledTerminalModules();
  const disabledModules = getDisabledTerminalModules();

  return (
    <section className="terminal-help-module" data-testid="terminal-help-module" id="terminal-help" tabIndex={-1}>
      <TerminalPanel
        eyebrow="Workspace help"
        title="Module and workflow reference"
        description="Use the module rail and market monitor actions to open API-backed workflows; navigation never invokes natural-language routing, broker order submission, or backend AI tools."
        actions={<TerminalStatusBadge tone="info">HELP</TerminalStatusBadge>}
      >
        <p className="terminal-help-module__summary">HOME, SEARCH, WATCHLIST, CHART, ANALYSIS, STATUS, and HELP remain reachable from the module rail or workflow actions while browser-visible data stays behind ATrade.Api.</p>
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
                <span>Search, trending, and watchlist rows can open chart or analysis workspaces while preserving exact provider identity.</span>
              </li>
              <li>
                <strong>Chart and analysis</strong>
                <span>Symbol routes hand off provider, provider symbol id, exchange, currency, asset class, and selected range where available.</span>
              </li>
              <li>
                <strong>Status</strong>
                <span>Provider diagnostics and paper-only state stay visible without hiding unavailable runtime states behind fake data.</span>
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
          <li>All browser-visible data flows through ATrade.Api; the frontend does not connect directly to IBKR/iBeam, Postgres, TimescaleDB, Redis, NATS, or LEAN.</li>
          <li>Provider-not-configured, provider-unavailable, authentication-required, and no-analysis-engine states remain explicit instead of falling back to fake market data.</li>
          <li>Orders are disabled by the paper-only safety contract. This workspace contains no order tickets, buy/sell controls, previews, or submit actions.</li>
        </ul>
      </TerminalPanel>
    </section>
  );
}
