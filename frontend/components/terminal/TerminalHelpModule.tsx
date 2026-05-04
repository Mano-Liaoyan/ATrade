import { TERMINAL_COMMAND_DEFINITIONS, TERMINAL_COMMAND_HELP } from "@/lib/terminalCommandRegistry";
import { getDisabledTerminalModules, getEnabledTerminalModules } from "@/lib/terminalModuleRegistry";
import { TerminalPanel } from "./TerminalPanel";
import { TerminalStatusBadge } from "./TerminalStatusBadge";

export function TerminalHelpModule() {
  const enabledModules = getEnabledTerminalModules();
  const disabledModules = getDisabledTerminalModules();

  return (
    <section className="terminal-help-module" data-testid="terminal-help-module" id="terminal-help" tabIndex={-1}>
      <TerminalPanel
        eyebrow="ATrade Terminal help"
        title="Deterministic command and module reference"
        description="Commands parse locally, route to enabled modules, and never invoke natural-language routing, broker order submission, or backend AI tools."
        actions={<TerminalStatusBadge tone="info">HELP</TerminalStatusBadge>}
      >
        <p className="terminal-help-module__summary">{TERMINAL_COMMAND_HELP}</p>
        <div className="terminal-help-module__grid">
          <div>
            <h3>Commands</h3>
            <dl className="terminal-help-module__commands">
              {TERMINAL_COMMAND_DEFINITIONS.map((command) => (
                <div key={command.command}>
                  <dt>{command.label}</dt>
                  <dd>{command.description}</dd>
                </div>
              ))}
            </dl>
          </div>
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
          <li>Orders are disabled by the paper-only safety contract. This terminal shell contains no order tickets, buy/sell controls, previews, or submit actions.</li>
        </ul>
      </TerminalPanel>
    </section>
  );
}
